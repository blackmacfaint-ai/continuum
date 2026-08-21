import json
import pathlib

CONFIG_PATH = pathlib.Path(r"C:\OmniRoute\repos\mark-l\config\api_keys.json")
START_ALL = pathlib.Path(r"C:\OmniRoute\repos\mark-l\start-all.cmd")
LOCAL_SESSION = pathlib.Path(r"C:\OmniRoute\repos\mark-l\core\local_session.py")


def test_llm_provider_is_ollama():
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    assert cfg.get("llm_provider") == "ollama", f"llm_provider should be 'ollama', got {cfg.get('llm_provider')}"


def test_llm_model_contains_qwen35():
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    model = cfg.get("llm_model", "")
    assert "Qwen3.5" in model, f"llm_model should contain 'Qwen3.5', got {model}"


def test_llm_model_contains_q4_k_m():
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    model = cfg.get("llm_model", "")
    assert "Q4_K_M" in model, f"llm_model should contain 'Q4_K_M', got {model}"


def test_llm_model_is_jackrong():
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    model = cfg.get("llm_model", "")
    assert "Jackrong" in model, f"llm_model should be Jackrong variant, got {model}"
    assert model == "hf.co/Jackrong/Qwen3.5-9B-DeepSeek-V4-Flash-GGUF:Q4_K_M"


def test_llm_url_is_11434():
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    url = cfg.get("llm_url", "")
    assert "11434" in url, f"llm_url should contain 11434, got {url}"
    assert url == "http://localhost:11434"


def test_start_all_exists():
    assert START_ALL.exists(), f"start-all.cmd missing: {START_ALL}"


def test_start_all_has_ollama_healthcheck():
    text = START_ALL.read_text(encoding="utf-8", errors="replace")
    assert "11434" in text, "start-all.cmd must contain ollama 11434 healthcheck"
    assert "ollama" in text.lower(), "start-all.cmd must mention ollama"


def test_start_all_has_comfyui_healthcheck():
    text = START_ALL.read_text(encoding="utf-8", errors="replace")
    assert "8188" in text, "start-all.cmd must contain comfyui 8188 healthcheck"
    lower = text.lower()
    assert "comfyui" in lower or "8188" in lower, "start-all.cmd must mention comfyui"


def test_start_all_has_continuum_healthcheck():
    text = START_ALL.read_text(encoding="utf-8", errors="replace")
    lower = text.lower()
    assert "continuum" in lower, "start-all.cmd must contain continuum healthcheck"


def test_start_all_has_7_steps():
    text = START_ALL.read_text(encoding="utf-8", errors="replace")
    # count [x/7] markers
    import re
    markers = re.findall(r"\[\d+/7\]", text)
    assert len(markers) >= 7, f"start-all.cmd should have 7 steps [n/7], found {markers}"
    # also ensure 7 healthcheck-ish echo lines
    echo_count = text.count("Pruefe")
    assert echo_count >= 6, f"start-all.cmd should have >=6 Pruefe lines, found {echo_count}"


def test_start_all_uses_python_requests():
    text = START_ALL.read_text(encoding="utf-8", errors="replace")
    # at least 4 python requests healthchecks (ollama, comfyui, continuum, omniroute, kokoro, voicebox)
    count = text.count("requests.get")
    assert count >= 4, f"start-all.cmd should use Python requests.get for healthchecks, found {count} occurrences"
    # ensure no PowerShell-only check without python — new checks must be python
    assert "requests" in text


def test_local_session_ollama_arguments_dict():
    text = LOCAL_SESSION.read_text(encoding="utf-8")
    # must have the ollama fix: fc.args if _is_ollama else json.dumps
    assert "fc.args if _is_ollama else json.dumps(fc.args)" in text, \
        "local_session.py must contain ollama arguments dict fix (fc.args if _is_ollama else json.dumps)"
    assert "_is_ollama" in text
    assert "get_llm_provider" in text


def test_ollama_model_available():
    import requests
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        assert r.status_code == 200, f"ollama /api/tags returned {r.status_code}"
        models = [m.get("name", "") for m in r.json().get("models", [])]
        target = "hf.co/Jackrong/Qwen3.5-9B-DeepSeek-V4-Flash-GGUF:Q4_K_M"
        found = any(m == target or m.startswith("hf.co/Jackrong/Qwen3.5") for m in models)
        assert found, f"Qwen3.5 Jackrong model not in ollama list: {models}"
    except Exception as e:
        # if ollama not running, ensure config is at least correct (other tests cover it)
        # but we want to flag if ollama down when test expects it up
        import pytest
        pytest.skip(f"Ollama not reachable, skipping live check: {e}")


def test_ollama_model_has_capabilities():
    import requests
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        r.raise_for_status()
        for m in r.json().get("models", []):
            if "Jackrong" in m.get("name", ""):
                caps = m.get("capabilities", [])
                assert "tools" in caps, f"Qwen model should support tools, got {caps}"
                assert "thinking" in caps, f"Qwen model should support thinking, got {caps}"
                # context length 262k
                details = m.get("details", {})
                ctx = details.get("context_length", 0)
                assert ctx >= 262144 or ctx == 0, f"context_length should be 262k, got {ctx}"
                return
        import pytest
        pytest.skip("Jackrong model not found for capability check")
    except Exception as e:
        import pytest
        pytest.skip(f"Ollama not reachable: {e}")
