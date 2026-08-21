import pathlib


def test_checkpoint_exists():
    p = pathlib.Path(r"C:\OmniRoute\ComfyUI\models\checkpoints\realisticVisionV60B1_v51HyperVAE.safetensors")
    assert p.exists(), f"Checkpoint missing: {p}"
    assert p.stat().st_size > 1_900_000_000, f"Checkpoint too small: {p.stat().st_size}"


def test_checkpoint_sha256():
    import hashlib
    p = pathlib.Path(r"C:\Users\Sebastian\Downloads\realisticVisionV60B1_v51HyperVAE.safetensors")
    if not p.exists():
        return
    expected = "F47E942AD4C30D863AD7F53CB60145FFCD2118845DFA705CE8BD6B42E90C4A13"
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    assert h.hexdigest().upper() == expected.upper(), f"SHA256 mismatch: {h.hexdigest()}"
