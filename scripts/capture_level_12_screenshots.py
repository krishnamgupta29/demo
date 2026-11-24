"""Level 12 Automated Screenshot Suite for DENTRACE Pure-White Single-Page Workstation.

Captures:
1. Before Upload State (1920x1080 and 1366x768)
2. After Upload Analysis Workspace (1920x1080 and 1366x768)
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
SCREENSHOT_DIR = PROJECT_ROOT / "docs" / "screenshots" / "level_12"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_BIN = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", "C:/temp")) / "Temp" / "chrome_dentrace_profile_l12"


def poll_url(url: str, timeout: float = 15.0) -> bool:
  start = time.time()
  while time.time() - start < timeout:
    try:
      with urllib.request.urlopen(url, timeout=1.0) as resp:
        if resp.status == 200:
          return True
    except Exception:
      time.sleep(0.4)
  return False


async def capture_level_12_suite():
  resp = urllib.request.urlopen("http://127.0.0.1:9222/json").read()
  pages = json.loads(resp)
  page = next(p for p in pages if p.get("type") == "page")
  ws_url = page["webSocketDebuggerUrl"]
  print(f"[*] Attached to Chrome CDP via {ws_url}")

  async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
    msg_id = 0

    async def send_cmd(method: str, params: dict = None):
      nonlocal msg_id
      msg_id += 1
      payload = {"id": msg_id, "method": method, "params": params or {}}
      await ws.send(json.dumps(payload))
      while True:
        raw = await ws.recv()
        data = json.loads(raw)
        if data.get("id") == msg_id:
          return data.get("result", {})

    await send_cmd("Page.enable")
    await send_cmd("DOM.enable")
    await send_cmd("Runtime.enable")

    # 1. Capture Upload State (Before Upload) at 1920x1080
    print("\n[*] Capturing Upload State at 1920x1080...")
    await send_cmd("Emulation.setDeviceMetricsOverride", {
        "width": 1920,
        "height": 1080,
        "deviceScaleFactor": 1,
        "mobile": False,
    })
    await send_cmd("Page.navigate", {"url": "http://127.0.0.1:8000/"})
    await asyncio.sleep(2.5)

    res = await send_cmd("Page.captureScreenshot", {"format": "png"})
    img_bytes = base64.b64decode(res["data"])
    out_1920_upload = SCREENSHOT_DIR / "level_12_upload_state_1920x1080.png"
    out_1920_upload.write_bytes(img_bytes)
    im = Image.open(out_1920_upload)
    print(f"    [OK] Captured: {out_1920_upload.name} ({im.size[0]}x{im.size[1]}, {len(img_bytes)/1024:.1f} KB)")

    # 2. Capture Upload State at 1366x768
    print("\n[*] Capturing Upload State at 1366x768...")
    await send_cmd("Emulation.setDeviceMetricsOverride", {
        "width": 1366,
        "height": 768,
        "deviceScaleFactor": 1,
        "mobile": False,
    })
    await asyncio.sleep(1.2)
    res = await send_cmd("Page.captureScreenshot", {"format": "png"})
    img_bytes = base64.b64decode(res["data"])
    out_1366_upload = SCREENSHOT_DIR / "level_12_upload_state_1366x768.png"
    out_1366_upload.write_bytes(img_bytes)
    im = Image.open(out_1366_upload)
    print(f"    [OK] Captured: {out_1366_upload.name} ({im.size[0]}x{im.size[1]}, {len(img_bytes)/1024:.1f} KB)")

    # 3. Transform to Analysis Workspace by clicking "Load Verified Case"
    print("\n[*] Triggering transformation to Analysis Workspace...")
    await send_cmd("Emulation.setDeviceMetricsOverride", {
        "width": 1920,
        "height": 1080,
        "deviceScaleFactor": 1,
        "mobile": False,
    })
    click_script = """
    (() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const sampleBtn = buttons.find(b => b.textContent && (b.textContent.includes('Load Case') || b.textContent.includes('Load Verified Case')));
      if (sampleBtn) { sampleBtn.click(); return 'clicked'; }
      return 'not_found';
    })()
    """
    eval_res = await send_cmd("Runtime.evaluate", {"expression": click_script})
    print(f"    [+] Button click result: {eval_res.get('result', {}).get('value')}")

    # Wait for radiograph image and findings to render
    await asyncio.sleep(3.5)

    # 4. Capture Analysis Workspace at 1920x1080
    print("\n[*] Capturing Analysis Workspace at 1920x1080...")
    res = await send_cmd("Page.captureScreenshot", {"format": "png"})
    img_bytes = base64.b64decode(res["data"])
    out_1920_work = SCREENSHOT_DIR / "level_12_analysis_workspace_1920x1080.png"
    out_1920_work.write_bytes(img_bytes)
    im = Image.open(out_1920_work)
    print(f"    [OK] Captured: {out_1920_work.name} ({im.size[0]}x{im.size[1]}, {len(img_bytes)/1024:.1f} KB)")

    # 5. Capture Analysis Workspace at 1366x768
    print("\n[*] Capturing Analysis Workspace at 1366x768...")
    await send_cmd("Emulation.setDeviceMetricsOverride", {
        "width": 1366,
        "height": 768,
        "deviceScaleFactor": 1,
        "mobile": False,
    })
    await asyncio.sleep(1.5)
    res = await send_cmd("Page.captureScreenshot", {"format": "png"})
    img_bytes = base64.b64decode(res["data"])
    out_1366_work = SCREENSHOT_DIR / "level_12_analysis_workspace_1366x768.png"
    out_1366_work.write_bytes(img_bytes)
    im = Image.open(out_1366_work)
    print(f"    [OK] Captured: {out_1366_work.name} ({im.size[0]}x{im.size[1]}, {len(img_bytes)/1024:.1f} KB)")


def main():
  print("=" * 70)
  print("  DENTRACE Level 12 Single-Page Automated Screenshot Suite")
  print("=" * 70)

  if not poll_url("http://127.0.0.1:8000/api/v1/health", timeout=2.0):
    print("[ERROR] FastAPI backend is not running on port 8000.")
    sys.exit(1)

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
    asyncio.run(capture_level_12_suite())
    print("\n[SUCCESS] All Level 12 screenshots captured and verified!")
  finally:
    chrome_proc.terminate()


if __name__ == "__main__":
  main()

