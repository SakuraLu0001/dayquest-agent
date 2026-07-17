"""Safe local smoke test for the DayQuest Streamable HTTP MCP server."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


ENDPOINT = "http://127.0.0.1:8080/mcp"
EXPECTED_TOOLS = {
    "get_safe_day_events",
    "get_dayquest_privacy_contract",
    "get_dayquest_status",
}
ALLOWED_EVENT_FIELDS = {
    "safe_event_id",
    "approximate_time",
    "event_type",
    "safe_summary",
    "source",
    "sensitivity",
    "redacted",
}
FORBIDDEN_KEYS = {
    "email",
    "email_body",
    "phone",
    "address",
    "amount",
    "order",
    "order_id",
    "token",
    "api_key",
    "evidence",
    "event_id",
}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\w)")
AMOUNT_RE = re.compile(r"\$\s?\d+(?:\.\d{2})?")
ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+(?:[A-Z][\w'-]*\s+){0,3}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\b",
    re.IGNORECASE,
)


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


def _privacy_check(records: Any) -> bool:
    if not isinstance(records, list) or not records:
        return False
    serialized = json.dumps(records, ensure_ascii=False)
    for record in records:
        if not isinstance(record, dict):
            return False
        lowered_keys = {str(key).lower() for key in record}
        if lowered_keys != ALLOWED_EVENT_FIELDS or lowered_keys & FORBIDDEN_KEYS:
            return False
        if record.get("redacted") is not True:
            return False
    return not any(
        pattern.search(serialized)
        for pattern in (EMAIL_RE, PHONE_RE, AMOUNT_RE, ADDRESS_RE)
    )


async def _run_smoke() -> dict[str, Any]:
    async with streamable_http_client(ENDPOINT) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            listed = await session.list_tools()
            tool_names = {tool.name for tool in listed.tools}
            status_result = await session.call_tool("get_dayquest_status")
            events_result = await session.call_tool(
                "get_safe_day_events",
                arguments={"limit": 3},
            )
            if getattr(status_result, "isError", False):
                raise ValueError("status_tool_error")
            if getattr(events_result, "isError", False):
                raise ValueError("events_tool_error")
            status = _unwrap_result(status_result)
            records = _unwrap_result(events_result)
            if not isinstance(status, dict) or status.get("service") != "DayQuest Privacy Gateway":
                raise ValueError("status_schema")
            return {
                "status": "success",
                "endpoint": ENDPOINT,
                "tool_count": len(tool_names),
                "expected_tools_present": EXPECTED_TOOLS.issubset(tool_names),
                "safe_event_count": len(records) if isinstance(records, list) else 0,
                "privacy_check_passed": _privacy_check(records),
                "error_type": None,
            }


def _safe_error_type(exc: BaseException) -> str:
    if isinstance(exc, httpx.ConnectTimeout):
        return "connect_timeout"
    if isinstance(exc, httpx.ReadTimeout):
        return "read_timeout"
    if isinstance(exc, httpx.ConnectError):
        return "connect_error"
    if isinstance(exc, ValueError):
        error_type = str(exc)
        if error_type in {
            "invalid_tool_result",
            "status_tool_error",
            "events_tool_error",
            "status_schema",
        }:
            return error_type
        return "validation_error"
    return "client_error"


def main() -> int:
    try:
        result = asyncio.run(_run_smoke())
    except Exception as exc:
        result = {
            "status": "failure",
            "endpoint": ENDPOINT,
            "tool_count": None,
            "expected_tools_present": False,
            "safe_event_count": None,
            "privacy_check_passed": False,
            "error_type": _safe_error_type(exc),
        }
    success = bool(
        result["status"] == "success"
        and result["expected_tools_present"]
        and result["safe_event_count"] == 3
        and result["privacy_check_passed"]
    )
    if not success:
        result["status"] = "failure"
    print(json.dumps(result, ensure_ascii=True), flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
