"""Level 11 Automated Screenshot Suite for DENTRACE React Frontend.

Captures all 7 views and responsive resolutions using Chrome DevTools Protocol (CDP).
Saves to docs/screenshots/level_11/
"""

import asyncio
import base64
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

SCREENSHOT_DIR = PROJECT_ROOT / "docs" / "screenshots" / "level_11"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_BIN = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", "C:/temp")) / "Temp" / "chrome_dentrace_profile_l11"


def poll_url(url: str, timeout: float = 20.0) -> bool:
  start = time.time()
  while time.time() - start < timeout:
    try:
      with urllib.request.urlopen(url, timeout=1.0) as resp:
        if resp.status == 200:
          return True
    except Exception:
      time.sleep(0.5)
  return False


async def capture_suite():
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
      ("fdi", "FDI Tooth Explorer"),
      ("evidence", "Clinical Evidence"),
      ("preauth", "Pre-Authorization Studio"),
      ("settings", "System Settings"),
  ]

  async with websockets.connect(ws_url, max_size=100 * 1024 * 1024) as ws:
    msg_id = 1

    async def send_cmd(method: str, params: dict | None = None):
      nonlocal msg_id
      payload = {"id": msg_id, "method": method, "params": params or {}}
      msg_id += 1
      await ws.send(json.dumps(payload))
      while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("id") == payload["id"]:
          return msg.get("result", {})

    # 1. Capture All 7 Views at 1920x1080
    for slug, label in views:
      target_url = f"http://127.0.0.1:8000/{slug}"
      print(f"\n[*] Navigating to {label}: {target_url}")

      # Set 1920x1080 viewport
      await send_cmd("Emulation.setDeviceMetricsOverride", {
          "width": 1920,
          "height": 1080,
          "deviceScaleFactor": 1,
          "mobile": False,
      })

      await send_cmd("Page.navigate", {"url": target_url})
      # Wait for React mount and WebGL render
      await asyncio.sleep(2.5)

      # Capture screenshot
      res = await send_cmd("Page.captureScreenshot", {"format": "png"})
      img_bytes = base64.b64decode(res["data"])
      out_path = SCREENSHOT_DIR / f"{slug}_1920x1080.png"
      out_path.write_bytes(img_bytes)

      im = Image.open(out_path)
      print(f"    [OK] Captured: {out_path.name} ({im.size[0]}x{im.size[1]}, {len(img_bytes)/1024:.1f} KB)")

    # 2. Capture Responsive Resolutions
    responsive_tests = [
        ("workstation", 1440, 900),
        ("workstation", 1366, 768),
        ("workstation", 1024, 768),
        ("overview", 768, 1024),
    ]

    for slug, w, h in responsive_tests:
      print(f"\n[*] Capturing Responsive Viewport: {slug} at {w}x{h}")
      await send_cmd("Emulation.setDeviceMetricsOverride", {
          "width": w,
          "height": h,
          "deviceScaleFactor": 1,
          "mobile": False,
      })
      await send_cmd("Page.navigate", {"url": f"http://127.0.0.1:8000/{slug}"})
      await asyncio.sleep(2.0)

      res = await send_cmd("Page.captureScreenshot", {"format": "png"})
      img_bytes = base64.b64decode(res["data"])
      out_path = SCREENSHOT_DIR / f"{slug}_{w}x{h}.png"
      out_path.write_bytes(img_bytes)

      im = Image.open(out_path)
      print(f"    [OK] Captured: {out_path.name} ({im.size[0]}x{im.size[1]}, {len(img_bytes)/1024:.1f} KB)")


def main():
  print("=" * 70)
  print("  DENTRACE Level 11 Automated Chrome Screenshot Suite")
  print("=" * 70)

  # Check if backend is already listening on 8000
  backend_proc = None
  if not poll_url("http://127.0.0.1:8000/api/v1/health", timeout=1.0):
    print("[*] Starting FastAPI Backend on 127.0.0.1:8000...")
    py_exec = sys.executable
    backend_proc = subprocess.Popen(
        [py_exec, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if not poll_url("http://127.0.0.1:8000/api/v1/health", timeout=15.0):
      print("[ERROR] FastAPI backend failed to start.")
      if backend_proc:
        backend_proc.kill()
      sys.exit(1)
    print("    [+] FastAPI Backend is healthy.")
  else:
    print("[*] Using already running FastAPI Backend on 127.0.0.1:8000.")

  # Launch Chrome in headless CDP mode
  if USER_DATA_DIR.exists():
    shutil.rmtree(USER_DATA_DIR, ignore_errors=True)
  USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

  chrome_cmd = [
      CHROME_BIN,
      "--headless=new",
      "--remote-debugging-port=9222",
      f"--user-data-dir={USER_DATA_DIR}",
      "--disable-gpu",
      "--no-first-run",
      "--no-default-browser-check",
      "--window-size=1920,1080",
      "about:blank",
  ]
  print("[*] Launching Headless Chrome with Remote Debugging...")
  chrome_proc = subprocess.Popen(chrome_cmd)

  time.sleep(2.0)

  try:
    asyncio.run(capture_suite())
    print("\n[SUCCESS] All Level 11 screenshots successfully captured and verified!")
  finally:
    chrome_proc.terminate()
    if backend_proc:
      backend_proc.terminate()
    shutil.rmtree(USER_DATA_DIR, ignore_errors=True)


if __name__ == "__main__":
  main()

