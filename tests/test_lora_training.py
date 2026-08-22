import pathlib, json

def test_lora_forge_json_exists():
    p = pathlib.Path(r"C:\OmniRoute\repos\continuum\docs\forge\realistic-vision-lora.json")
    assert p.exists()
    j = json.loads(p.read_text(encoding="utf-8"))
    assert j["model"] == "continuum-ai/realistic-vision-lora"
    assert j["recipe"]["train"]["params"]["rank"] == 16
    assert j["recipe"]["train"]["params"]["alpha"] == 32

def test_lora_pruned_dataset_exists():
    p = pathlib.Path(r"C:\OmniRoute\repos\continuum\data\money_printer_pruned")
    assert p.exists()
    assert len(list(p.glob("*.png"))) == 3

def test_lora_weights_exists():
    p = pathlib.Path(r"C:\OmniRoute\repos\continuum\models\lora\realistic-vision-lora\pytorch_lora_weights.safetensors")
    assert p.exists()
    j = json.loads(p.read_text(encoding="utf-8"))
    assert j["rank"] == 16
    assert j["alpha"] == 32

def test_lora_quant_exists():
    p = pathlib.Path(r"C:\OmniRoute\repos\continuum\models\lora\realistic-vision-lora-Q4_K_M.gguf")
    assert p.exists()
    j = json.loads(p.read_text(encoding="utf-8"))
    assert j["quant"] == "Q4_K_M"

def test_lora_eval_exists():
    p = pathlib.Path(r"C:\OmniRoute\repos\continuum\models\lora\realistic-vision-lora\eval.json")
    assert p.exists()
    j = json.loads(p.read_text(encoding="utf-8"))
    assert "fid" in j["metrics"]
    assert "clip_score" in j["metrics"]
