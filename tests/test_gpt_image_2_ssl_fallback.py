"""SSL cert fallback for gpt_image_2.

When the system SSL bundle fails verification (common on Python.org
installs that do not pick up certifi automatically), the helper should
retry once with an SSL context built from certifi's CA bundle.
"""
import os
import ssl
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "styled-carousel", "scripts"),
)
import gpt_image_2  # type: ignore[reportMissingImports]


def _make_response():
    m = MagicMock()
    m.read.return_value = b'{"data":[{"b64_json":"ZmFrZQ=="}]}'
    m.__enter__ = lambda _: m
    m.__exit__ = lambda *_: None
    return m


def test_is_ssl_cert_error_detects_url_error_wrap():
    from urllib.error import URLError
    inner = ssl.SSLCertVerificationError(1, "CERTIFICATE_VERIFY_FAILED")
    wrapped = URLError(inner)
    assert gpt_image_2._is_ssl_cert_error(wrapped) is True


def test_is_ssl_cert_error_false_for_other_url_errors():
    from urllib.error import URLError
    assert gpt_image_2._is_ssl_cert_error(URLError("connection refused")) is False


def test_is_ssl_cert_error_detects_bare_ssl_error_str():
    err = ssl.SSLError("CERTIFICATE_VERIFY_FAILED detail")
    assert gpt_image_2._is_ssl_cert_error(err) is True


@patch.object(gpt_image_2, "HAS_CERTIFI", True)
@patch.object(gpt_image_2, "certifi", create=True)
@patch("gpt_image_2.ssl.create_default_context")
@patch("gpt_image_2.urlopen")
def test_open_with_cert_fallback_retries_with_certifi(
    mock_urlopen, mock_create_ctx, mock_certifi
):
    from urllib.error import URLError
    mock_certifi.where.return_value = "/fake/certifi/cacert.pem"
    fake_ctx = MagicMock(spec=ssl.SSLContext)
    mock_create_ctx.return_value = fake_ctx
    inner = ssl.SSLCertVerificationError(1, "CERTIFICATE_VERIFY_FAILED")
    err = URLError(inner)
    good = _make_response()
    mock_urlopen.side_effect = [err, good]

    result = gpt_image_2._open_with_cert_fallback(MagicMock(), timeout=30)

    assert result is good
    assert mock_urlopen.call_count == 2
    mock_create_ctx.assert_called_once_with(cafile="/fake/certifi/cacert.pem")
    second_call_kwargs = mock_urlopen.call_args_list[1].kwargs
    assert second_call_kwargs.get("context") is fake_ctx


@patch.object(gpt_image_2, "HAS_CERTIFI", False)
@patch("gpt_image_2.urlopen")
def test_open_with_cert_fallback_raises_when_certifi_missing(mock_urlopen):
    from urllib.error import URLError
    inner = ssl.SSLCertVerificationError(1, "CERTIFICATE_VERIFY_FAILED")
    err = URLError(inner)
    mock_urlopen.side_effect = err

    with pytest.raises(URLError):
        gpt_image_2._open_with_cert_fallback(MagicMock(), timeout=30)


@patch("gpt_image_2.urlopen")
def test_open_with_cert_fallback_passes_through_non_ssl_errors(mock_urlopen):
    from urllib.error import URLError
    err = URLError("connection refused")
    mock_urlopen.side_effect = err

    with pytest.raises(URLError):
        gpt_image_2._open_with_cert_fallback(MagicMock(), timeout=30)
    # Should not retry for non-SSL URL errors.
    assert mock_urlopen.call_count == 1


@patch.object(gpt_image_2, "HAS_CERTIFI", True)
@patch.object(gpt_image_2, "certifi", create=True)
@patch("gpt_image_2.ssl.create_default_context")
@patch("gpt_image_2.urlopen")
def test_generate_recovers_from_ssl_error(
    mock_urlopen, mock_create_ctx, mock_certifi, tmp_path
):
    """End-to-end: generate() should succeed when first call hits SSL verify error."""
    from urllib.error import URLError
    mock_certifi.where.return_value = "/fake/certifi/cacert.pem"
    mock_create_ctx.return_value = MagicMock(spec=ssl.SSLContext)
    inner = ssl.SSLCertVerificationError(1, "CERTIFICATE_VERIFY_FAILED")
    err = URLError(inner)
    good = _make_response()
    mock_urlopen.side_effect = [err, good]

    out = tmp_path / "slide.png"
    gpt_image_2.generate(
        prompt="test",
        size="1024x1024",
        output_path=str(out),
        api_key="sk-test",
        retry_delays=[],
    )
    assert out.exists()
    assert out.stat().st_size > 0
