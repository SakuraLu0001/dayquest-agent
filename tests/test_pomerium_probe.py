from __future__ import annotations

from pathlib import Path

import httpx

from dayquest.pomerium_probe import PomeriumProbeConfig, PomeriumRouteProbe


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_SECRET = "private-response-body-token"


class FakeResponse:
    def __init__(self, status_code: int, location: str = "") -> None:
        self.status_code = status_code
        self.headers = {"location": location, "set-cookie": TEST_SECRET}
        self.body = TEST_SECRET


class FakeClient:
    def __init__(self, response: FakeResponse | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls = 0
        self.kwargs: dict[str, object] | None = None

    def get(self, _url: str, **kwargs: object) -> FakeResponse:
        self.calls += 1
        self.kwargs = kwargs
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


def _probe(client: FakeClient) -> PomeriumRouteProbe:
    return PomeriumRouteProbe(
        PomeriumProbeConfig(
            route_url="https://protected.example.invalid/mcp",
            timeout_seconds=8,
        ),
        client=client,
    )


def test_401_verifies_connected_gateway_protection() -> None:
    client = FakeClient(FakeResponse(401))

    status = _probe(client).probe()

    assert status["connected"] is True
    assert status["protection_verified"] is True
    assert status["http_status"] == 401
    assert status["error_type"] is None
    assert client.kwargs == {"timeout": 8, "follow_redirects": False}


def test_authentication_redirect_verifies_protection() -> None:
    for status_code in (302, 303):
        status = _probe(
            FakeClient(
                FakeResponse(
                    status_code,
                    "https://authenticate.example.invalid/oauth/authorize?private=value",
                )
            )
        ).probe()

        assert status["connected"] is True
        assert status["protection_verified"] is True
        assert status["http_status"] == status_code


def test_non_authentication_redirect_is_not_accepted() -> None:
    status = _probe(
        FakeClient(FakeResponse(302, "https://public.example.invalid/landing"))
    ).probe()

    assert status["connected"] is False
    assert status["protection_verified"] is False
    assert status["error_type"] == "gateway_unavailable"


def test_timeout_is_safely_classified() -> None:
    status = _probe(FakeClient(error=httpx.ConnectTimeout(TEST_SECRET))).probe()

    assert status["connected"] is False
    assert status["protection_verified"] is False
    assert status["error_type"] == "connect_timeout"
    assert TEST_SECRET not in repr(status)


def test_missing_route_does_not_make_network_request() -> None:
    client = FakeClient(FakeResponse(401))
    probe = PomeriumRouteProbe(PomeriumProbeConfig(), client=client)

    status = probe.probe()

    assert client.calls == 0
    assert status["configured"] is False
    assert status["attempted"] is False
    assert status["error_type"] == "missing_config"


def test_status_does_not_store_body_oauth_url_cookie_or_credentials() -> None:
    oauth_url = "https://login.example.invalid/oauth/authorize?user=private"
    status = _probe(FakeClient(FakeResponse(303, oauth_url))).probe()
    serialized = repr(status)

    assert set(status) == {
        "configured",
        "attempted",
        "connected",
        "protection_verified",
        "http_status",
        "latency_ms",
        "role",
        "error_type",
    }
    for forbidden in (
        TEST_SECRET,
        oauth_url,
        "set-cookie",
        "authorization",
        "response body",
    ):
        assert forbidden.lower() not in serialized.lower()


def test_streamlit_ui_uses_only_verified_pomerium_status() -> None:
    source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")

    assert "Pomerium: Connected" in source
    assert "Protected MCP route verified: Yes" in source
    assert "Unauthenticated access blocked: Yes" in source
    assert "Local MCP tools verified: Yes" in source
    assert "authenticated remote MCP tool invocation" not in source
