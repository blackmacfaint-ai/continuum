#!/usr/bin/env python3
"""artifacts/store helper - kopiert Artefakt nach data/artifacts/files/<type>/<id>.<ext> und registriert es.

Usage:
  python scripts/artifacts_store.py --artifact C:/path/clip.mp4 --type video --tags e2e
  python scripts/artifacts_store.py --artifact img.png --type image --registry C:/tmp/registry.json

Prints a JSON result on stdout:
  {"success": true, "artifactId": "abc123def456", "path": "..."}
"""
import argparse
import json
import pathlib
import shutil
import sys
import uuid

REPO_ROOT = pathlib.Path(__file__).parent.parent
DEFAULT_REGISTRY = REPO_ROOT / "data" / "artifacts" / "registry.json"


def parse_args():
    ap = argparse.ArgumentParser(description="Store artifact in registry")
    ap.add_argument("--artifact", required=True, help="Path to the artifact file")
    ap.add_argument("--type", choices=["video", "image", "audio", "document"], required=True)
    ap.add_argument("--tags", nargs="*", default=[])
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="Registry JSON path")
    ap.add_argument("--dry-run", action="store_true", help="Validate args without storing")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    src = pathlib.Path(args.artifact)
    if not src.exists():
        print(json.dumps({"success": False, "error": f"artifact not found: {src}"}))
        return 1
    artifact_id = uuid.uuid4().hex[:12]
    registry = pathlib.Path(args.registry)
    if args.dry_run:
        print(json.dumps({"success": True, "artifactId": artifact_id, "path": str(src), "dryRun": True}))
        return 0

    target_dir = registry.parent / "files" / args.type
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{artifact_id}{src.suffix.lower()}"
    shutil.copy2(src, target)

    entries = []
    if registry.exists():
        entries = json.loads(registry.read_text(encoding="utf-8"))
    entries.append({
        "artifactId": artifact_id,
        "type": args.type,
        "path": str(target),
        "source": str(src),
        "tags": list(args.tags),
        "createdAt": "2026-08-23",
    })
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    print(json.dumps({"success": True, "artifactId": artifact_id, "path": str(target)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
