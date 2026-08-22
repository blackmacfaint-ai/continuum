import json
import pathlib

def test_forge_contract_exists():
    p = pathlib.Path(r"C:\OmniRoute\repos\continuum\docs\forge\realistic-vision-lora.json")
    assert p.exists(), f"missing {p}"
    alloy = json.loads(p.read_text(encoding="utf-8"))
    assert alloy["recipe"] is not None

def test_forge_contract_has_prun_train_quant_eval():
    p = pathlib.Path(r"C:\OmniRoute\repos\continuum\docs\forge\realistic-vision-lora.json")
    alloy = json.loads(p.read_text(encoding="utf-8"))
    assert alloy["model"] == "continuum-ai/realistic-vision-lora"
    assert "realisticVisionV60B1" in alloy["base"]
    for k in ["prun", "train", "quant", "eval"]:
        assert k in alloy["recipe"], f"missing {k} in recipe"

def test_forge_md_exists():
    p = pathlib.Path(r"C:\OmniRoute\repos\continuum\docs\forge\realistic-vision-lora.md")
    assert p.exists()
    assert "continuum-ai/realistic-vision-lora" in p.read_text(encoding="utf-8")
