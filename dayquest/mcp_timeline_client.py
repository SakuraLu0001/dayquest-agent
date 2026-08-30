"""Real localhost MCP transport for the evidence-carrying timeline slice."""

from __future__ import annotations

import asyncio
import json
import os
import re
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from .pomerium_mcp_server import (
    MCP_ENDPOINT,
    MCP_HOST,
    MCP_PORT,
    SAFE_EVENT_FIELDS,
    SAFE_EVENT_ID_HASH_BASIS,
    SAFE_EVENT_ID_SCHEMA,
)


EXPECTED_TOOLS = {
    "get_safe_day_events",
    "get_dayquest_privacy_contract",
    "get_dayquest_status",
}
FORBIDDEN_KEYS = {
    "address",
    "api_key",
    "authorization",
    "credential",
    "email_body",
    "evidence",
    "headers",
    "local_path",
    "order_id",
    "payload",
    "phone",
    "secret",
    "session_token",
    "token",
}
_ABSOLUTE_WINDOWS_PATH = re.compile(r"\b[A-Za-z]:[\\/]")
_PRIVATE_TEXT = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"(?<!\w)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\w)"),
    re.compile(r"\$\s?\d+(?:\.\d{2})?"),
    re.compile(r"(?i)\b(?:bearer\s+|sk-)[A-Za-z0-9._-]{8,}"),
)
_PROVIDER_ENV_KEYS = {
    "AKASH_API_KEY",
    "NEXLA_SESSION_TOKEN",
    "POMERIUM_ROUTE_URL",
}


def _unwrap_result(result: Any) -> Any:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        if set(structured) == {"result"}:
            return structured["result"]
        return structured
    content = getattr(result, "content", None)
    if isinstance(content, list) and content:
        text = getattr(content[0], "text", None)
        if isinstance(text, str):
            return json.loads(text)
    raise ValueError("invalid_tool_result")


def _validate_safe_records(records: Any) -> list[dict[str, Any]]:
    if not isinstance(records, list) or not records:
        raise ValueError("safe_events_missing")
    serialized = json.dumps(records, ensure_ascii=False)
    if _ABSOLUTE_WINDOWS_PATH.search(serialized):
        raise ValueError("absolute_path_in_safe_events")
    if any(pattern.search(serialized) for pattern in _PRIVATE_TEXT):
        raise ValueError("private_text_in_safe_events")
    for record in records:
        if not isinstance(record, dict) or set(record) != SAFE_EVENT_FIELDS:
            raise ValueError("safe_event_schema_invalid")
        if {str(key).lower() for key in record} & FORBIDDEN_KEYS:
            raise ValueError("forbidden_safe_event_field")
        if record.get("redacted") is not True:
            raise ValueError("safe_event_not_redacted")
        if record.get("safe_identity_schema") != SAFE_EVENT_ID_SCHEMA:
            raise ValueError("safe_identity_schema_invalid")
    return records


async def fetch_timeline_inputs(limit: int) -> dict[str, Any]:
    """Read safe events through a real Streamable HTTP MCP session."""

    async with streamable_http_client(MCP_ENDPOINT) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            listed = await session.list_tools()
            tool_names = sorted(tool.name for tool in listed.tools)
            if not EXPECTED_TOOLS.issubset(tool_names):
                raise ValueError("required_mcp_tools_missing")

            status_result = await session.call_tool("get_dayquest_status")
            privacy_result = await session.call_tool("get_dayquest_privacy_contract")
            events_result = await session.call_tool(
                "get_safe_day_events",
                arguments={"limit": limit, "local_only": True},
            )
            if any(
                getattr(result, "isError", False)
                for result in (status_result, privacy_result, events_result)
            ):
                raise ValueError("mcp_tool_error")

            status = _unwrap_result(status_result)
            privacy = _unwrap_result(privacy_result)
            events = _validate_safe_records(_unwrap_result(events_result))
            if not isinstance(status, dict) or status.get("service") != "DayQuest Privacy Gateway":
                raise ValueError("mcp_status_invalid")
            if not isinstance(privacy, dict) or privacy.get("raw_data_exposed") is not False:
                raise ValueError("mcp_privacy_contract_invalid")
            if set(privacy.get("allowed_fields", [])) != SAFE_EVENT_FIELDS:
                raise ValueError("mcp_privacy_allowlist_invalid")
            if privacy.get("safe_identity_schema") != SAFE_EVENT_ID_SCHEMA:
                raise ValueError("mcp_safe_identity_schema_invalid")
            if privacy.get("safe_identity_hash_basis") != SAFE_EVENT_ID_HASH_BASIS:
                raise ValueError("mcp_safe_identity_hash_basis_invalid")
            if privacy.get("safe_identity_is_confidentiality_primitive") is not False:
                raise ValueError("mcp_safe_identity_privacy_semantics_invalid")

            return {
                "events": events,
                "transport": {
                    "endpoint": MCP_ENDPOINT,
                    "transport": "streamable-http",
                    "real_transport": True,
                    "local_only": True,
                    "network_scope": "loopback_only",
                    "secret_required": False,
                    "tool_names": tool_names,
                    "tool_calls": [
                        "get_dayquest_status",
                        "get_dayquest_privacy_contract",
                        "get_safe_day_events",
                    ],
                    "event_count": len(events),
                    "privacy_raw_data_exposed": False,
                    "safe_identity_schema": SAFE_EVENT_ID_SCHEMA,
                    "safe_identity_hash_basis": SAFE_EVENT_ID_HASH_BASIS,
                    "safe_identity_is_confidentiality_primitive": False,
                },
            }


def is_mcp_port_open() -> bool:
    try:
        with socket.create_connection((MCP_HOST, MCP_PORT), timeout=0.1):
            return True
    except OSError:
        return False


def _wait_for_port(*, expected_open: bool, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if is_mcp_port_open() is expected_open:
            return True
        time.sleep(0.05)
    return is_mcp_port_open() is expected_open


@contextmanager
def running_local_mcp_server(project_root: Path) -> Iterator[None]:
    """Start and fully reap the repository's localhost FastMCP process."""

    if is_mcp_port_open():
        raise RuntimeError("mcp_port_8080_in_use")
    child_env = os.environ.copy()
    for key in _PROVIDER_ENV_KEYS:
        child_env.pop(key, None)
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    process = subprocess.Popen(
        [sys.executable, "-B", "-m", "dayquest.pomerium_mcp_server"],
        cwd=project_root,
        env=child_env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    try:
        if not _wait_for_port(expected_open=True, timeout_seconds=8):
            raise RuntimeError("local_mcp_server_start_failed")
        if process.poll() is not None:
            raise RuntimeError("local_mcp_server_exited_early")
        yield
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if not _wait_for_port(expected_open=False, timeout_seconds=5):
            raise RuntimeError("local_mcp_server_residue")
