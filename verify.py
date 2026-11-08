"""Verify the four published archives without extracting or executing them."""
from pathlib import Path
import hashlib
import json

def main() -> None:
    root = Path(__file__).resolve().parent
    receipts = sorted((root / "archives").glob("*.json"))
    if len(receipts) != 4:
        raise RuntimeError("Expected exactly four archive receipts")
    for path in receipts:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        archive = path.with_suffix(".tar.gz")
        digest = hashlib.sha256()
        with archive.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if archive.stat().st_size != receipt["archive_bytes"] or digest.hexdigest() != receipt["archive_sha256"]:
            raise RuntimeError(f"Archive mismatch: {archive.name}; run git lfs pull")
        print(f"Verified {archive.name}")

if __name__ == "__main__":
    main()
