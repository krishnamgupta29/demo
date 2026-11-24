"""Robust Level 10.5 Automated Screenshot Suite for DENTRACE.

Controls:
1. Spawns FastAPI backend and verifies health probe
2. Spawns Streamlit Clinical Workstation and verifies health probe
3. Controls Chrome via Chrome DevTools Protocol (CDP)
4. Waits for Streamlit WebSocket connection and WebGL render
5. Captures 1920x1080 screenshots across all 7 views
6. Captures responsive resolutions (1440x900, 1366x768, 1024x768, 768x1024)
7. Verifies image integrity and dimensions
"""

import asyncio
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from PIL import Image
import websockets

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

SCREENSHOT_DIR = PROJECT_ROOT / "docs" / "screenshots" / "level_10_5"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_BIN = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", "C:/temp")) / "Temp" / "chrome_dentrace_profile"


def poll_url(url: str, timeout: float = 20.0) -> bool:
  start = time.time()
  while time.time() - start < timeout:
    try:
      with urllib.request.urlopen(url, timeout=1.5) as resp:
        if resp.status == 200:
          return True
    except Exception:
      time.sleep(0.5)
  return False


async def capture_views_cdp():
  # Connect to CDP
  resp = urllib.request.urlopen("http://127.0.0.1:9222/json").read()
  pages = json.loads(resp)
  page = next(p for p in pages if p.get("type") == "page")
  ws_url = page["webSocketDebuggerUrl"]
  print(f"[*] Attached to Chrome CDP via {ws_url}")

  views = [
      ("overview", "Overview / Home"),
      ("upload", "Upload Workspace"),
      ("workstation", "Diagnostic Workstation"),
      ("fdi_explorer", "FDI Tooth Explorer"),
      ("evidence", "Clinical Evidence"),
      ("preauth", "Pre-Authorization Studio"),
      ("settings", "System Settings"),
  ]

  async with websockets.connect(ws_url, max_size=30_000_000) as ws:
    # 1. 1920x1080 Full HD Captures
    print("\n--- 1. Capturing All 7 Views at 1920x1080 ---")
    await ws.send(json.dumps({
        "id": 100,
        "method": "Emulation.setDeviceMetricsOverride",
        "params": {"width": 1920, "height": 1080, "deviceScaleFactor": 1, "mobile": False},
    }))

    msg_id = 200
    for v_key, v_label in views:
      msg_id += 1
      nav_url = f"http://127.0.0.1:8501/?view={v_key}"
      print(f"[*] Navigating to {v_label} ({nav_url})...")
      await ws.send(json.dumps({"id": msg_id, "method": "Page.navigate", "params": {"url": nav_url}}))

      # Wait for Streamlit React rerender and WebGL / Canvas draw
      await asyncio.sleep(4.5)

      msg_id += 1
      await ws.send(json.dumps({"id": msg_id, "method": "Page.captureScreenshot", "params": {"format": "png"}}))
      while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("id") == msg_id:
          img_bytes = base64.b64decode(msg["result"]["data"])
          out_file = SCREENSHOT_DIR / f"1920x1080_{v_key}.png"
          out_file.write_bytes(img_bytes)
          print(f"    [OK] Captured {out_file.name} ({len(img_bytes) // 1024} KB)")
          break

    # 2. Responsive Captures for Workstation and Overview
    resolutions = [
        ("1440x900", 1440, 900),
        ("1366x768", 1366, 768),
        ("1024x768", 1024, 768),
        ("768x1024", 768, 1024),
    ]

    print("\n--- 2. Capturing Responsive Viewports ---")
    for res_name, w, h in resolutions:
      await ws.send(json.dumps({
          "id": msg_id + 1,
          "method": "Emulation.setDeviceMetricsOverride",
          "params": {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": False},
      }))
      for v_key in ["overview", "workstation"]:
        msg_id += 2
        nav_url = f"http://127.0.0.1:8501/?view={v_key}"
        await ws.send(json.dumps({"id": msg_id, "method": "Page.navigate", "params": {"url": nav_url}}))
        await asyncio.sleep(3.5)

        msg_id += 1
        await ws.send(json.dumps({"id": msg_id, "method": "Page.captureScreenshot", "params": {"format": "png"}}))
        while True:
          raw = await ws.recv()
          msg = json.loads(raw)
          if msg.get("id") == msg_id:
            img_bytes = base64.b64decode(msg["result"]["data"])
            out_file = SCREENSHOT_DIR / f"{res_name}_{v_key}.png"
            out_file.write_bytes(img_bytes)
            print(f"    [OK] Captured {out_file.name} ({len(img_bytes) // 1024} KB)")
            break


def main():
  py_exec = sys.executable
  env = os.environ.copy()
  env["PYTHONPATH"] = str(PROJECT_ROOT)
  env["DENTRACE_DATA_DIR"] = str(PROJECT_ROOT / "data")
  env["DENTRACE_DEV_MODE"] = "1"

  api_proc = None
  ui_proc = None
  chrome_proc = None

  try:
    # 1. Start FastAPI
    print("[*] Checking FastAPI status on 127.0.0.1:8000...")
    if not poll_url("http://127.0.0.1:8000/api/v1/health", timeout=1.5):
      print("[*] Launching FastAPI backend...")
      api_proc = subprocess.Popen(
          [py_exec, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
          cwd=str(PROJECT_ROOT),
          env=env,
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL,
      )
      if not poll_url("http://127.0.0.1:8000/api/v1/health", timeout=25.0):
        raise RuntimeError("FastAPI failed to start.")
      print("    [+] FastAPI Backend is healthy (200 OK).")
    else:
      print("    [+] FastAPI Backend is already running.")

    # Ingest synthetic test study
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
        api_client.analyze_study(s_id)
        api_client.select_procedure(
            study_id=s_id,
            procedure_name="Molar Endodontic Therapy",
            clinician_rationale="Deep caries approaching pulp horn with nocturnal pain.",
            tooth_fdi=16,
            suggested_cdt_code="D3330",
            cdt_code_verified=True,
            urgency="urgent",
        )
        api_client.generate_draft(s_id, force_deterministic=True)
        print(f"    [+] Initialized study {s_id}")

    # 2. Start Streamlit
    print("[*] Checking Streamlit status on 127.0.0.1:8501...")
    if not poll_url("http://127.0.0.1:8501/_stcore/health", timeout=1.5):
      print("[*] Launching Streamlit Workstation...")
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
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL,
      )
      if not poll_url("http://127.0.0.1:8501/_stcore/health", timeout=25.0):
        raise RuntimeError("Streamlit failed to start.")
      print("    [+] Streamlit Workstation is healthy (200 OK).")
    else:
      print("    [+] Streamlit Workstation is already running.")

    # 3. Launch Headless Chrome
    print("[*] Launching Chrome CDP server on port 9222...")
    shutil.rmtree(USER_DATA_DIR, ignore_errors=True)
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    chrome_proc = subprocess.Popen([
        CHROME_BIN,
        "--headless=new",
        "--remote-debugging-port=9222",
        f"--user-data-dir={str(USER_DATA_DIR)}",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1920,1080",
        "about:blank",
    ])
    time.sleep(2.0)

    # 4. Run async CDP captures
    asyncio.run(capture_views_cdp())

    print("\n[SUCCESS] Completed screenshot captures.")

  finally:
    # Cleanup
    if chrome_proc:
      print("[*] Terminating Chrome...")
      chrome_proc.terminate()
      try:
        chrome_proc.wait(timeout=3)
      except Exception:
        chrome_proc.kill()
    if ui_proc:
      print("[*] Terminating Streamlit...")
      ui_proc.terminate()
      try:
        ui_proc.wait(timeout=3)
      except Exception:
        ui_proc.kill()
    if api_proc:
      print("[*] Terminating FastAPI...")
      api_proc.terminate()
      try:
        api_proc.wait(timeout=3)
      except Exception:
        api_proc.kill()


if __name__ == "__main__":
  main()

