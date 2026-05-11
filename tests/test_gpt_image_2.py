import sys, os, json
from email.message import Message
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "styled-carousel", "scripts"))
import gpt_image_2  # type: ignore[reportMissingImports]


def fake_response(b64="ZmFrZQ=="):
    m = MagicMock()
    m.read.return_value = json.dumps({
        "data": [{"b64_json": b64}]
    }).encode("utf-8")
    m.__enter__ = lambda _: m
    m.__exit__ = lambda *_: None
    return m


@patch("gpt_image_2.urlopen")
def test_generate_writes_png(mock_urlopen, tmp_path):
    mock_urlopen.return_value = fake_response()
    out = tmp_path / "slide-01-1024x1024.png"
    gpt_image_2.generate(
        prompt="test",
        size="1024x1024",
        output_path=str(out),
        api_key="sk-test"
    )
    assert out.exists()
    assert out.stat().st_size > 0


@patch("gpt_image_2.urlopen")
def test_generate_retries_on_rate_limit(mock_urlopen, tmp_path):
    from urllib.error import HTTPError
    bad = HTTPError("u", 429, "Rate limited", Message(), None)
    good = fake_response()
    mock_urlopen.side_effect = [bad, good]
    out = tmp_path / "slide.png"
    gpt_image_2.generate(
        prompt="test", size="1024x1024",
        output_path=str(out), api_key="sk-test",
        retry_delays=[0]
    )
    assert out.exists()


def test_generate_dry_run_writes_prompt_file_no_api(tmp_path):
    out = tmp_path / "slide.png"
    gpt_image_2.generate(
        prompt="dry test", size="1024x1024",
        output_path=str(out), api_key=None, dry_run=True
    )
    assert (tmp_path / "slide.prompt.txt").exists()
    assert not out.exists()


def test_generate_raises_when_no_api_key_and_not_dry(tmp_path):
    with pytest.raises(SystemExit):
        gpt_image_2.generate(
            prompt="x", size="1024x1024",
            output_path=str(tmp_path / "s.png"),
            api_key=None, dry_run=False
        )


def _fake_curl_completed(b64="ZmFrZQ=="):
    m = MagicMock()
    m.stdout = json.dumps({"data": [{"b64_json": b64}]})
    m.returncode = 0
    return m


@patch("gpt_image_2.subprocess.run")
def test_generate_with_reference_uses_edits_endpoint(mock_run, tmp_path):
    mock_run.return_value = _fake_curl_completed()
    ref = tmp_path / "ref-front.png"
    ref.write_bytes(b"fake-png-bytes")
    out = tmp_path / "slide-01-1024x1024.png"
    gpt_image_2.generate(
        prompt="test",
        size="1024x1024",
        output_path=str(out),
        api_key="sk-test",
        reference_images=[str(ref)],
    )
    assert out.exists()
    assert out.stat().st_size > 0
    assert mock_run.called
    args, _ = mock_run.call_args
    cmd = args[0]
    # The first positional arg to subprocess.run is the curl argv list.
    assert "curl" in cmd[0]
    joined = " ".join(cmd)
    assert "https://api.openai.com/v1/images/edits" in joined


def test_generate_with_reference_dry_run_emits_prompt_file(tmp_path):
    ref = tmp_path / "ref-front.png"
    ref.write_bytes(b"fake-png-bytes")
    out = tmp_path / "slide.png"
    gpt_image_2.generate(
        prompt="dry test with ref",
        size="1024x1024",
        output_path=str(out),
        api_key=None,
        dry_run=True,
        reference_images=[str(ref)],
    )
    assert (tmp_path / "slide.prompt.txt").exists()
    assert not out.exists()


@patch("gpt_image_2.subprocess.run")
def test_generate_with_multiple_references_passes_all(mock_run, tmp_path):
    mock_run.return_value = _fake_curl_completed()
    ref1 = tmp_path / "ref-front.png"
    ref2 = tmp_path / "ref-three-quarter.png"
    ref1.write_bytes(b"a")
    ref2.write_bytes(b"b")
    out = tmp_path / "slide.png"
    gpt_image_2.generate(
        prompt="test",
        size="1024x1024",
        output_path=str(out),
        api_key="sk-test",
        reference_images=[str(ref1), str(ref2)],
    )
    args, _ = mock_run.call_args
    cmd = args[0]
    joined = " ".join(cmd)
    assert f"image[]=@{ref1}" in joined
    assert f"image[]=@{ref2}" in joined


@patch("gpt_image_2.subprocess.run")
def test_generate_via_edits_n5_returns_five_paths(mock_run, tmp_path):
    payload = {"data": [{"b64_json": "ZmFrZQ=="} for _ in range(5)]}
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = json.dumps(payload)
    mock_run.return_value = fake

    out = tmp_path / "slide.png"
    ref = tmp_path / "ref.png"
    ref.write_bytes(b"fake-ref-bytes")

    result = gpt_image_2.generate(
        prompt="multi-panel test",
        size="1024x1024",
        output_path=str(out),
        api_key="sk-test",
        reference_images=[str(ref)],
        n=5,
    )

    assert "output_paths" in result
    assert len(result["output_paths"]) == 5
    for p in result["output_paths"]:
        assert os.path.exists(p)
        assert os.path.getsize(p) > 0
    assert result["n"] == 5
