import urllib.request
import hashlib
from pathlib import Path
import time
import sys

def download_file(url: str, target: Path, expected_size: int = None) -> tuple[int, str]:
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading from {url} to {target}...")
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(target, "wb") as out_f:
        downloaded = 0
        while True:
            chunk = resp.read(1024 * 512)
            if not chunk:
                break
            out_f.write(chunk)
            downloaded += len(chunk)
    elapsed = time.time() - t0
    
    sha256 = hashlib.sha256()
    with open(target, "rb") as f:
        while b := f.read(1024 * 1024):
            sha256.update(b)
    digest = sha256.hexdigest()
    actual_size = target.stat().st_size
    print(f"Downloaded {target.name}: {actual_size} bytes in {elapsed:.2f}s ({actual_size / (1024*1024*elapsed):.2f} MB/s)")
    print(f"SHA-256: {digest}")
    if expected_size and actual_size != expected_size:
        raise ValueError(f"Size mismatch: expected {expected_size}, got {actual_size}")
    return actual_size, digest

def main():
    checkpoint_dir = Path("C:/mini/models/checkpoints")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    items = [
        {
            "url": "https://huggingface.co/liodon-ai/dental-panoramic-detector/resolve/main/best.onnx",
            "target": checkpoint_dir / "best.onnx",
            "expected_size": 10605711,
        },
        {
            "url": "https://huggingface.co/abychkov/dental-fdi-detection/resolve/main/dental_fdi.onnx",
            "target": checkpoint_dir / "dental_fdi.onnx",
            "expected_size": 130754966,
        }
    ]

    results = {}
    for item in items:
        size, digest = download_file(item["url"], item["target"], item["expected_size"])
        results[item["target"].name] = {"size": size, "sha256": digest}

    print("\nDownload Summary:")
    for k, v in results.items():
        print(f"  {k}: size={v['size']}, sha256={v['sha256']}")

if __name__ == "__main__":
    main()
