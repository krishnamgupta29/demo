"""Automated Screenshot Capture and Verification Suite for DENTRACE Level 10.5.

Executes:
1. Process supervision for FastAPI backend and Streamlit Workstation
2. Health & readiness verification
3. Populates synthetic/real study if database empty
4. Headless Chrome screenshot capture across all 7 views:
   - Overview
   - Upload Workspace
   - Diagnostic Workstation
   - FDI Tooth Explorer
   - Clinical Evidence
   - Pre-Authorization Studio
   - System Settings
5. Responsive resolution captures (1920x1080, 1440x900, 1366x768, 1024x768, 768x1024)
6. Clean process teardown
"""

import io
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# Ensure UTF-8 console output
try:
  sys.stdout.reconfigure(encoding='utf-8')
except Exception:
  pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image

SCREENSHOT_DIR = PROJECT_ROOT / "docs" / "screenshots" / "level_10_5"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser() -> str:
  for p in CHROME_PATHS:
    if os.path.exists(p):
      return p
  raise RuntimeError("No Chromium/Edge browser found for screenshot capture.")


def poll_url(url: str, timeout: float = 15.0) -> bool:
  start = time.time()
  while time.time() - start < timeout:
    try:
      with urllib.request.urlopen(url, timeout=1.5) as resp:
        if resp.status == 200:
          return True
    except Exception:
      time.sleep(0.5)
  return False


def main():
  browser_bin = find_browser()
  print(f"[*] Found Browser for Verification: {browser_bin}")
  py_exec = sys.executable

  # Environment
  env = os.environ.copy()
  env["PYTHONPATH"] = str(PROJECT_ROOT)
  env["DENTRACE_DATA_DIR"] = str(PROJECT_ROOT / "data")
  env["DENTRACE_DEV_MODE"] = "1"

  api_proc = None
  ui_proc = None

  try:
    # 1. Start FastAPI backend if not already listening
    if not poll_url("http://127.0.0.1:8000/api/v1/health", timeout=1.5):
      print("[*] Spawning FastAPI backend process...")
      api_proc = subprocess.Popen(
          [py_exec, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
          cwd=str(PROJECT_ROOT),
          env=env,
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL,
      )
      if not poll_url("http://127.0.0.1:8000/api/v1/health", timeout=30.0):
        raise RuntimeError("FastAPI failed to start within 30 seconds.")
      print("    [+] FastAPI Backend is healthy.")
    else:
      print("    [+] FastAPI Backend is already running.")

    # Ingest a sample study if none exist
    from frontend.api_client import api_client
    studies = api_client.list_studies()
    if not studies:
      print("[*] Ingesting test study into database...")
      img = Image.new("L", (800, 400), color=75)
      buf = io.BytesIO()
      img.save(buf, format="PNG")
      up_res = api_client.upload_study(
          file_bytes=buf.getvalue(),
          filename="sample_opg.png",
          patient_anonymous_id="PT-LEVEL10-DEMO",
          clinical_indication="Level 10.5 Visual Overhaul Demonstration Case",
      )
      if up_res.get("success"):
        s_id = up_res["data"]["study_id"]
        print(f"    [+] Ingested demo study {s_id}")
        # Run screener
        api_client.analyze_study(s_id)
        # Select procedure
        api_client.select_procedure(
            study_id=s_id,
            procedure_name="Molar Endodontic Therapy",
            clinician_rationale="Deep caries approaching pulp horn with nocturnal pain.",
            tooth_fdi=16,
            suggested_cdt_code="D3330",
            cdt_code_verified=True,
            urgency="urgent",
        )
        # Generate draft
        api_client.generate_draft(s_id, force_deterministic=True)

    # 2. Start Streamlit if not already listening
    if not poll_url("http://127.0.0.1:8501/_stcore/health", timeout=1.0):
      print("[*] Spawning Streamlit workstation process...")
      ui_proc = subprocess.Popen(
          [
              py_exec,
              "-m",
              "streamlit",
              "run",
              "frontend/app.py",
              "--server.port",
              "8501",
              "--server.address",
              "127.0.0.1",
              "--server.headless",
              "true",
              "--browser.gatherUsageStats",
              "false",
          ],
          cwd=str(PROJECT_ROOT),
          env=env,
      )
      if not poll_url("http://127.0.0.1:8501/_stcore/health", timeout=20.0):
        raise RuntimeError("Streamlit failed to start within 20 seconds.")
      print("    [+] Streamlit Workstation is healthy.")
    else:
      print("    [+] Streamlit Workstation is already running.")

    # 3. Capture All 7 Views at 1920x1080
    views = [
        ("overview", "Overview / Home"),
        ("upload", "Upload Workspace"),
        ("workstation", "Diagnostic Workstation"),
        ("fdi_explorer", "FDI Tooth Explorer"),
        ("evidence", "Clinical Evidence"),
        ("preauth", "Pre-Authorization Studio"),
        ("settings", "System Settings"),
    ]

    print("\n[*] Capturing Baseline & Redesigned Screenshots at 1920x1080...")
    for v_key, v_label in views:
      out_path = SCREENSHOT_DIR / f"1920x1080_{v_key}.png"
      target_url = f"http://127.0.0.1:8501/?view={v_key}"
      print(f"    [-] Capturing view: {v_label} -> {out_path.name}")
      cmd = [
          browser_bin,
          "--headless=new",
          "--disable-gpu",
          "--hide-scrollbars",
          "--window-size=1920,1080",
          "--virtual-time-budget=6000",
          f"--screenshot={str(out_path)}",
          target_url,
      ]
      subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
      if out_path.exists():
        print(f"        [OK] Saved ({out_path.stat().st_size // 1024} KB)")

    # 4. Capture Responsive Resolutions for Key Screens
    resolutions = [
        ("1440x900", 1440, 900),
        ("1366x768", 1366, 768),
        ("1024x768", 1024, 768),
        ("768x1024", 768, 1024),
    ]

    print("\n[*] Capturing Responsive Resolutions for Diagnostic Workstation & Overview...")
    for res_name, w, h in resolutions:
      for v_key in ["overview", "workstation"]:
        out_path = SCREENSHOT_DIR / f"{res_name}_{v_key}.png"
        target_url = f"http://127.0.0.1:8501/?view={v_key}"
        cmd = [
            browser_bin,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--window-size={w},{h}",
            "--virtual-time-budget=6000",
            f"--screenshot={str(out_path)}",
            target_url,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if out_path.exists():
          print(f"    [OK] Captured {res_name} {v_key} ({out_path.stat().st_size // 1024} KB)")

    print("\n[SUCCESS] All Level 10.5 screenshots captured successfully!")

  finally:
    # Clean shutdown
    if ui_proc:
      print("[*] Terminating Streamlit subprocess...")
      ui_proc.terminate()
      try:
        ui_proc.wait(timeout=3)
      except Exception:
        ui_proc.kill()
    if api_proc:
      print("[*] Terminating FastAPI subprocess...")
      api_proc.terminate()
      try:
        api_proc.wait(timeout=3)
      except Exception:
        api_proc.kill()


if __name__ == "__main__":
  main()
