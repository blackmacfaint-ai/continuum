import io
import json
import sys
import unittest.mock
import urllib.error

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "scripts"))

import ai_generate


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _resp(payload: dict):
    return FakeResp(json.dumps(payload).encode())


def test_request_includes_system_message():
    """Der Ollama-Fix: Qwen3.5-GGUFs brauchen ein system-Message, sonst leere Antwort."""
    seen = {}

    def fake_urlopen(req, timeout=300):
        seen["body"] = json.loads(req.data)
        return _resp({"message": {"content": "Hallo"}})

    with unittest.mock.patch.object(ai_generate.urllib.request, "urlopen", fake_urlopen):
        code = ai_generate.main()

    assert code == 0
    roles = [m["role"] for m in seen["body"]["messages"]]
    assert roles == ["system", "user"], f"expected [system, user], got {roles}"


def test_falls_back_when_primary_returns_empty():
    """Primaermodell liefert leeren Content -> naechstes Modell der Kette wird genutzt."""
    calls = []

    def fake_urlopen(req, timeout=300):
        calls.append(json.loads(req.data))
        if len(calls) == 1:
            return _resp({"message": {"content": ""}})
        return _resp({"message": {"content": "Fallback-Text"}})

    with unittest.mock.patch.object(ai_generate.urllib.request, "urlopen", fake_urlopen):
        out = io.StringIO()
        with unittest.mock.patch.object(sys, "stdout", out):
            code = ai_generate.main()

    assert code == 0
    result = json.loads(out.getvalue())
    assert result["success"] is True
    assert result["model"] == "llama3.1:8b-instruct-q4_K_M"
    assert len(calls) == 2


def test_fails_cleanly_when_all_models_empty():
    def fake_urlopen(req, timeout=300):
        return _resp({"message": {"content": ""}})

    with unittest.mock.patch.object(ai_generate.urllib.request, "urlopen", fake_urlopen):
        out = io.StringIO()
        with unittest.mock.patch.object(sys, "stdout", out):
            code = ai_generate.main()

    assert code == 1
    result = json.loads(out.getvalue())
    assert result["success"] is False
    assert "empty" in result["error"]


def test_dry_run_returns_success():
    out = io.StringIO()
    with unittest.mock.patch.object(sys, "argv", ["ai_generate.py", "--prompt", "x", "--dry-run"]), unittest.mock.patch.object(sys, "stdout", out):
        code = ai_generate.main()
    assert code == 0
    assert json.loads(out.getvalue())["success"] is True


def test_empty_prompt_fails():
    out = io.StringIO()
    with unittest.mock.patch.object(sys, "argv", ["ai_generate.py", "--prompt", ""]), unittest.mock.patch.object(sys, "stdout", out):
        code = ai_generate.main()
    assert code == 1


def test_ollama_unreachable_fails_cleanly():
    def fake_urlopen(req, timeout=300):
        raise urllib.error.URLError("connection refused")

    out = io.StringIO()
    with unittest.mock.patch.object(ai_generate.urllib.request, "urlopen", fake_urlopen), unittest.mock.patch.object(sys, "stdout", out):
        code = ai_generate.main()
    assert code == 1
    assert "unreachable" in json.loads(out.getvalue())["error"]


@pytest.fixture(autouse=True)
def _argv():
    with unittest.mock.patch.object(
        sys, "argv", ["ai_generate.py", "--prompt", "Test-Prompt"]
    ):
        yield
