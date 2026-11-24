"""Verify fresh clone setup with release zip in a temp folder on C:\."""

import shutil
import zipfile
import subprocess
import hashlib
from pathlib import Path

def test_fresh_setup():
    temp_dir = Path("C:/temp_dentrace_verify")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created temp directory: {temp_dir}")
    
    # 1. Unzip default release models zip into temp dir
    zip_path = Path("C:/release/dentrace_models_default_v1.0.zip")
    assert zip_path.exists(), f"Release zip not found at {zip_path}"
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    print(f"Extracted {zip_path.name} into {temp_dir}")
    
    # Check extracted files
    extracted_files = list(temp_dir.rglob("*"))
    print(f"Found {len(extracted_files)} items in {temp_dir}:")
    for f in extracted_files:
        if f.is_file():
            print(f"  - {f.relative_to(temp_dir)} ({f.stat().st_size:,} bytes)")
            
    # Verify checksums using SHA256SUMS.txt
    checksum_file = temp_dir / "SHA256SUMS.txt"
    if not checksum_file.exists():
        # Check inside subdirs
        candidates = list(temp_dir.rglob("SHA256SUMS.txt"))
        if candidates:
            checksum_file = candidates[0]
            
    assert checksum_file.exists(), "SHA256SUMS.txt missing from release zip!"
    print(f"Found checksum file: {checksum_file}")
    
    failed_hashes = []
    with open(checksum_file, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            expected_hash, rel_path = line.split(None, 1)
            target_file = temp_dir / rel_path.replace("/", "\\")
            if not target_file.exists():
                failed_hashes.append(f"Missing file: {rel_path}")
                continue
            calc_hash = hashlib.sha256(target_file.read_bytes()).hexdigest().lower()
            if calc_hash != expected_hash.lower():
                failed_hashes.append(f"Hash mismatch on {rel_path}: expected {expected_hash}, got {calc_hash}")
            else:
                print(f"  [OK] Hash verified: {rel_path}")
                
    if failed_hashes:
        print("FAILURES DETECTED:")
        for fh in failed_hashes:
            print("  *", fh)
        return False
    else:
        print("\nAll release models verified successfully with 100% SHA-256 match!")
        return True

if __name__ == "__main__":
    success = test_fresh_setup()
    if not success:
        exit(1)
