"""Security regression tests for DocImprintClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from docimprint.client import DocImprintClient
from docimprint.errors import DocImprintError


@pytest.fixture
def client() -> DocImprintClient:
    return DocImprintClient("dr_test_key", base_url="https://api.docimprint.com")


# --- HTTPS enforcement ---


def test_https_base_url_accepted() -> None:
    c = DocImprintClient("key", base_url="https://api.docimprint.com")
    assert c.base_url == "https://api.docimprint.com"


def test_localhost_http_accepted() -> None:
    c = DocImprintClient("key", base_url="http://127.0.0.1:8080")
    assert c.base_url == "http://127.0.0.1:8080"


def test_localhost_name_http_accepted() -> None:
    c = DocImprintClient("key", base_url="http://localhost:9000")
    assert c.base_url == "http://localhost:9000"


def test_insecure_http_rejected() -> None:
    with pytest.raises(DocImprintError) as exc:
        DocImprintClient("key", base_url="http://evil.com")
    assert exc.value.code == "INSECURE_BASE_URL"


def test_insecure_http_allowed_with_flag() -> None:
    c = DocImprintClient("key", base_url="http://evil.com", allow_insecure_http=True)
    assert c.base_url == "http://evil.com"


# --- API key redaction ---


def test_client_repr_redacts_api_key() -> None:
    c = DocImprintClient("dr_super_secret_key")
    text = repr(c)
    assert "dr_super_secret_key" not in text
    assert "***" in text


def test_api_key_not_public_attribute() -> None:
    c = DocImprintClient("dr_secret")
    assert not hasattr(c, "api_key")


# --- ID validation blocks path traversal before HTTP ---


@pytest.mark.parametrize(
    ("method_name", "args", "kwargs"),
    [
        ("verify", ("../../v1/quota",), {}),
        ("notarize", ("../admin",), {}),
        ("delete_bundle", ("ev_abc/../../quota",), {}),
        ("get_bundle", ("..%2F..%2Fv1%2Fquota",), {}),
        ("add_to_collection", ("col_1", "../../secrets"), {}),
        ("search_collection", ("../other", "q"), {}),
        ("ask_collection", ("col_../x", "q"), {}),
        ("get_job", ("../../jobs",), {}),
        ("wait_for_job", ("job_../x",), {}),
        ("log_provenance", ("ev_../x", "agent", "read"), {}),
        ("handoff", ("ev_abc/foo", "a", "b"), {}),
    ],
)
def test_invalid_ids_raise_before_http(
    client: DocImprintClient,
    method_name: str,
    args: tuple,
    kwargs: dict,
) -> None:
    method = getattr(client, method_name)
    with patch.object(client, "_request", side_effect=AssertionError("HTTP must not be called")):
        with pytest.raises(DocImprintError) as exc:
            method(*args, **kwargs)
    assert exc.value.code == "INVALID_ID"


@pytest.mark.parametrize(
    ("method_name", "args", "kwargs"),
    [
        ("verify", ("ev_abc123",), {}),
        ("notarize", ("ev_test",), {}),
        ("get_bundle", ("ev_x",), {}),
        ("add_to_collection", ("col_1", "ev_abc"), {}),
        ("search_collection", ("col_search", "query"), {}),
        ("ask_collection", ("col_ask", "question?"), {}),
        ("get_job", ("job_1",), {}),
        ("log_provenance", ("ev_1", "agent-a", "read"), {}),
        ("handoff", ("ev_1", "agent-a", "agent-b"), {}),
    ],
)
@respx.mock
def test_valid_ids_reach_http(
    client: DocImprintClient,
    method_name: str,
    args: tuple,
    kwargs: dict,
) -> None:
    respx.route(url__regex=r"https://api\.docimprint\.com/.*").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    method = getattr(client, method_name)
    if method_name == "delete_bundle":
        method(*args, **kwargs)
    else:
        result = method(*args, **kwargs)
        assert result is not None or method_name == "delete_bundle"


def test_path_traversal_does_not_hit_unintended_endpoint(client: DocImprintClient) -> None:
    """Traversal segments must be rejected locally, not normalized by httpx."""
    mock_http = MagicMock()
    client._http = mock_http
    with pytest.raises(DocImprintError) as exc:
        client.verify("../../v1/quota")
    assert exc.value.code == "INVALID_ID"
    mock_http.request.assert_not_called()
