"""Safe, read-only probe for the protected Pomerium MCP route."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx


POMERIUM_ROLE = "Authenticated MCP privacy gateway"
AUTH_REDIRECT_MARKERS = ("authorize", "oauth", "login", "sign-in", "signin")


@dataclass(frozen=True)
class PomeriumProbeConfig:
    route_url: str = ""
    timeout_seconds: float = 8.0


def _status(
    *,
    configured: bool,
    attempted: bool,
    connected: bool = False,
    protection_verified: bool = False,
    http_status: int | None = None,
    latency_ms: int | None = None,
    error_type: str | None = None,
) -> dict[str, Any]:
    return {
        "configured": configured,
        "attempted": attempted,
        "connected": connected,
        "protection_verified": protection_verified,
        "http_status": http_status,
        "latency_ms": latency_ms,
        "role": POMERIUM_ROLE,
        "error_type": error_type,
    }


class PomeriumRouteProbe:
    def __init__(self, config: PomeriumProbeConfig, client: Any | None = None) -> None:
        self.config = config
        self._client = client
        self.configuration_error = self._configuration_error()

    @classmethod
    def from_env(cls) -> "PomeriumRouteProbe":
        timeout_raw = os.getenv("POMERIUM_TIMEOUT_SECONDS", "8")
        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = 0.0
        return cls(
            PomeriumProbeConfig(
                route_url=os.getenv("POMERIUM_ROUTE_URL", ""),
                timeout_seconds=timeout,
            )
        )

    @property
    def configured(self) -> bool:
        return self.configuration_error is None

    def _configuration_error(self) -> str | None:
        if not self.config.route_url:
            return "missing_config"
        parsed = urlparse(self.config.route_url)
        if parsed.scheme != "https" or not parsed.netloc:
            return "invalid_route_url"
        if self.config.timeout_seconds <= 0:
            return "invalid_timeout"
        return None

    def initial_status(self) -> dict[str, Any]:
        return _status(
            configured=self.configured,
            attempted=False,
            error_type=self.configuration_error,
        )

    def probe(self) -> dict[str, Any]:
        if self.configuration_error:
            return self.initial_status()
        started = time.perf_counter()
        owns_client = self._client is None
        client = self._client or httpx.Client(
            timeout=self.config.timeout_seconds,
            follow_redirects=False,
        )
        try:
            response = client.get(
                self.config.route_url,
                timeout=self.config.timeout_seconds,
                follow_redirects=False,
            )
            latency_ms = round((time.perf_counter() - started) * 1000)
            status_code = response.status_code
            protected = status_code == 401
            if status_code in {302, 303}:
                location = response.headers.get("location", "")
                protected = any(marker in location.lower() for marker in AUTH_REDIRECT_MARKERS)
            return _status(
                configured=True,
                attempted=True,
                connected=protected,
                protection_verified=protected,
                http_status=status_code,
                latency_ms=latency_ms,
                error_type=None if protected else "gateway_unavailable",
            )
        except httpx.ConnectTimeout:
            error_type = "connect_timeout"
        except httpx.ReadTimeout:
            error_type = "read_timeout"
        except httpx.ConnectError:
            error_type = "connect_error"
        except httpx.HTTPError:
            error_type = "http_client_error"
        except Exception:
            error_type = "probe_error"
        finally:
            if owns_client:
                client.close()
        return _status(
            configured=True,
            attempted=True,
            latency_ms=round((time.perf_counter() - started) * 1000),
            error_type=error_type,
        )
