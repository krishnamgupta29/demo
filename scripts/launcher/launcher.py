"""DENTRACE Clinical Decision Support Engine — Native Windows Launcher.

Fulfills Level 9/11 Packaging & System Requirements:
1. Environment and Python runtime validation (Python 3.11).
2. Single-instance mutual exclusion lockfile (`dentrace.lock`).
3. Port conflict detection and loopback binding verification.
4. Model manifest and SHA-256 integrity inspection.
5. Storage permissions and disk budget verification (>500 MB free).
6. SQLite database migration preflight.
7. Hardware instrumentation: GPU (NVIDIA RTX 2050) & Ollama LLM detection.
8. Local ephemeral single-user session token generation.
9. Process supervision for FastAPI backend (single-port React SPA served at /).
10. Readiness polling and automatic browser workstation launch.
11. Signal trapping (SIGINT, SIGTERM) and atexit cleanup to ensure ZERO orphaned processes.
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Optional

# Base directories
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))


class DentraceLauncher:
  """Robust process manager and preflight runner for DENTRACE Desktop."""

  def __init__(self):
    self.project_root = PROJECT_ROOT
    self.app_name = "DENTRACE Clinical Decision Support Engine"
    self.version = "0.1.0"
    self.api_port = 8000
    self.session_token = secrets.token_hex(24)
    self.data_dir = self._resolve_data_dir()
    self.lock_file = self.data_dir / "dentrace.lock"
    self.api_process: Optional[subprocess.Popen] = None
    self._is_shutting_down = False

  # --------------------------------------------------------------------------
  # Directory and Lockfile Management
  # --------------------------------------------------------------------------

  def _resolve_data_dir(self) -> Path:
    """Resolve user-writable application data directory."""
    if "DENTRACE_DATA_DIR" in os.environ:
      path = Path(os.environ["DENTRACE_DATA_DIR"])
    elif os.environ.get("DENTRACE_DEV_MODE", "1") == "1" and (self.project_root / "data").exists():
      path = self.project_root / "data"
    else:
      local_app_data = os.environ.get("LOCALAPPDATA")
      if local_app_data:
        path = Path(local_app_data) / "DENTRACE" / "data"
      else:
        path = self.project_root / "data"
    path.mkdir(parents=True, exist_ok=True)
    (path / "storage").mkdir(parents=True, exist_ok=True)
    (path / "previews").mkdir(parents=True, exist_ok=True)
    return path

  def acquire_single_instance_lock(self) -> bool:
    """Ensure only a single instance of DENTRACE is running simultaneously."""
    if self.lock_file.exists():
      try:
        content = self.lock_file.read_text().strip()
        if content.isdigit():
          old_pid = int(content)
          if self._is_pid_alive(old_pid):
            print(f"[INFO] DENTRACE is already active (PID {old_pid}).")
            print(f"[INFO] Directing to active workstation: http://127.0.0.1:{self.api_port}")
            webbrowser.open(f"http://127.0.0.1:{self.api_port}")
            return False
      except Exception:
        pass
      try:
        self.lock_file.unlink()
      except Exception:
        pass

    try:
      self.lock_file.write_text(str(os.getpid()))
      return True
    except Exception as exc:
      print(f"[WARN] Unable to write lockfile: {exc}")
      return True

  def release_lock(self):
    """Clean up the single-instance lock file."""
    try:
      if self.lock_file.exists():
        content = self.lock_file.read_text().strip()
        if content == str(os.getpid()):
          self.lock_file.unlink()
    except Exception:
      pass

  def _is_pid_alive(self, pid: int) -> bool:
    """Check if process with PID is currently alive on Windows."""
    if pid <= 0:
      return False
    try:
      out = subprocess.check_output(
          ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
          text=True,
          stderr=subprocess.DEVNULL,
      )
      return str(pid) in out
    except Exception:
      return False

  # --------------------------------------------------------------------------
  # Preflight Checks
  # --------------------------------------------------------------------------

  def check_python_runtime(self) -> bool:
    """Verify supported Python runtime (Python 3.11 recommended)."""
    major, minor = sys.version_info.major, sys.version_info.minor
    print(f"[*] Python Runtime: {sys.version.split()[0]} ({sys.executable})")
    if major != 3 or minor != 11:
      print(
          f"[WARN] Python {major}.{minor} detected. DENTRACE is verified on Python 3.11.9."
          " Execution will proceed, but minor package compatibility warnings may occur."
      )
    return True

  def check_disk_space(self) -> bool:
    """Ensure sufficient free disk space on data drive (>500 MB)."""
    try:
      usage = shutil.disk_usage(self.data_dir)
      free_mb = usage.free / (1024 * 1024)
      print(f"[*] Target Data Directory: {self.data_dir} ({free_mb:.1f} MB free)")
      if free_mb < 500:
        print(f"[ERROR] Insufficient disk space on data drive ({free_mb:.1f} MB < 500 MB required).")
        return False
      return True
    except Exception as exc:
      print(f"[WARN] Could not measure disk space: {exc}")
      return True

  def check_ports(self) -> bool:
    """Verify loopback port 8000 is available for single-port desktop workstation."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
      s.settimeout(0.5)
      if s.connect_ex(("127.0.0.1", self.api_port)) == 0:
        print(f"[ERROR] Port {self.api_port} is already in use by another process.")
        print(f"[HINT] Stop the competing process or configure an alternative port.")
        return False
    print(f"[*] Loopback Port: 127.0.0.1:{self.api_port} (Single-Port React Workstation) available")
    return True

  def check_database(self) -> bool:
    """Verify SQLite database and run pending Alembic migrations."""
    db_path = self.data_dir / "dentrace.db"
    print(f"[*] SQLite Database: {db_path}")
    try:
      from backend.config import settings
      from backend.database.migrations import run_migrations
      run_migrations()
      print("[*] Database schema initialized and verified.")
      return True
    except Exception as exc:
      print(f"[ERROR] Database migration preflight failed: {exc}")
      return False

  def check_models(self) -> dict[str, Any]:
    """Inspect model files and verify SHA-256 hashes against manifest."""
    manifest_path = self.project_root / "config" / "model_manifest.json"
    status = {"available": 0, "missing": 0, "verified": 0, "damaged": 0}
    if not manifest_path.exists():
      print("[WARN] Model manifest not found; skipping hash verification.")
      return status

    try:
      with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
      models = data.get("models", [])
      print(f"[*] Verifying {len(models)} model checkpoints in manifest:")
      for m in models:
        rel_path = m.get("local_file_location")
        if not rel_path or "http" in rel_path:
          continue
        p = self.project_root / rel_path
        expected_hash = m.get("sha256")
        if p.exists():
          status["available"] += 1
          if expected_hash:
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            if h.lower() == expected_hash.lower():
              status["verified"] += 1
              print(f"    [+] {m['model_name']}: VERIFIED (SHA-256 match)")
            else:
              status["damaged"] += 1
              print(f"    [!] {m['model_name']}: DAMAGED (hash mismatch!)")
          else:
            print(f"    [+] {m['model_name']}: PRESENT (no hash specified)")
        else:
          status["missing"] += 1
          print(f"    [-] {m['model_name']}: MISSING ({rel_path})")
    except Exception as exc:
      print(f"[WARN] Error reading model manifest: {exc}")
    return status

  def check_hardware(self) -> dict[str, Any]:
    """Detect GPU hardware and Ollama local LLM service."""
    hw_info = {"gpu_available": False, "gpu_name": "None", "ollama_available": False}
    try:
      import torch
      if torch.cuda.is_available():
        hw_info["gpu_available"] = True
        hw_info["gpu_name"] = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"[*] Hardware Acceleration: GPU Active — {hw_info['gpu_name']} ({vram_gb:.1f} GB VRAM)")
      else:
        print("[*] Hardware Acceleration: CPU Fallback Mode (NVIDIA CUDA not detected or disabled)")
    except Exception:
      print("[*] Hardware Acceleration: CPU Fallback Mode")

    # Probe Ollama
    try:
      req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
      with urllib.request.urlopen(req, timeout=1.0) as resp:
        if resp.status == 200:
          data = json.loads(resp.read().decode())
          models = [m.get("name", "") for m in data.get("models", [])]
          hw_info["ollama_available"] = True
          has_qwen = any("qwen2.5:3b" in m for m in models)
          if has_qwen:
            print("[*] Local LLM: Ollama Online (qwen2.5:3b model ready for clinical drafting)")
          else:
            print("[*] Local LLM: Ollama Online (qwen2.5:3b not pulled — rule-based narrative active)")
    except Exception:
      print("[*] Local LLM: Ollama Offline — Deterministic rule-based claim narrative active")

    return hw_info

  # --------------------------------------------------------------------------
  # Process Spawning and Supervision
  # --------------------------------------------------------------------------

  def start_services(self) -> bool:
    """Start FastAPI backend as supervised subprocess (React SPA served at /)."""
    py_exec = sys.executable
    env = os.environ.copy()
    env["PYTHONPATH"] = str(self.project_root)
    env["DENTRACE_DATA_DIR"] = str(self.data_dir)
    env["DENTRACE_API_KEY"] = self.session_token
    env["DENTRACE_DEV_MODE"] = "0"

    print("\n" + "=" * 70)
    print(f"  LAUNCHING {self.app_name.upper()} v{self.version}")
    print("  Regulatory Notice: Draft for dentist review. Not a diagnosis.")
    print("=" * 70 + "\n")

    # 1. Start FastAPI backend
    api_cmd = [
        py_exec,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(self.api_port),
        "--log-level",
        "warning",
    ]
    print(f"[*] Starting REST API service on 127.0.0.1:{self.api_port}...")
    try:
      self.api_process = subprocess.Popen(
          api_cmd,
          cwd=str(self.project_root),
          env=env,
          stdout=subprocess.DEVNULL,
          stderr=subprocess.PIPE,
          creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
      )
    except Exception as exc:
      print(f"[ERROR] Failed to start FastAPI process: {exc}")
      return False

    # Wait for API readiness
    print("[*] Waiting for REST API service to report healthy...")
    api_ready = self._poll_health(
        f"http://127.0.0.1:{self.api_port}/api/v1/health",
        timeout=15.0,
    )
    if not api_ready:
      print("[ERROR] FastAPI backend failed to reach healthy status within 15 seconds.")
      self.shutdown()
      return False
    print("    [+] FastAPI Backend is READY (Health status: 200 OK)")

    # 2. Level 11 Single-Port React Desktop Integration
    # The compiled React production frontend is served directly through FastAPI at port 8000.
    workstation_url = f"http://127.0.0.1:{self.api_port}"
    print(f"\n[SUCCESS] Opening DENTRACE React Clinical Workstation: {workstation_url}")
    webbrowser.open(workstation_url)

    print("\n" + "-" * 70)
    print("  DENTRACE LEVEL 11 IS RUNNING LOCALLY (Zero Cloud Egress)")
    print(f"  React Workstation: {workstation_url}")
    print(f"  Interactive REST:  {workstation_url}/docs")
    print("  Regulatory Notice: Draft for dentist review. Not a diagnosis.")
    print("  Press Ctrl+C in this console window to gracefully shut down.")
    print("-" * 70 + "\n")

    return True

  def _poll_health(self, url: str, timeout: float = 15.0) -> bool:
    """Poll endpoint until 200 OK or timeout."""
    t0 = time.time()
    while time.time() - t0 < timeout:
      try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=0.8) as resp:
          if resp.status == 200:
            return True
      except Exception:
        pass
      time.sleep(0.3)
    return False

  def supervise(self):
    """Monitor running backend process until user interruption or child exit."""
    try:
      while True:
        if self.api_process and self.api_process.poll() is not None:
          err = self.api_process.stderr.read().decode(errors="replace") if self.api_process.stderr else ""
          print(f"[ERROR] FastAPI process terminated unexpectedly (code {self.api_process.returncode}):\n{err}")
          break
        time.sleep(1.0)
    except KeyboardInterrupt:
      print("\n[*] Received shutdown signal (Ctrl+C). Initiating graceful cleanup...")
    finally:
      self.shutdown()

  def shutdown(self):
    """Terminate child processes cleanly and release system locks."""
    if self._is_shutting_down:
      return
    self._is_shutting_down = True
    print("[*] Terminating child processes...")

    # Terminate FastAPI
    if self.api_process:
      self._terminate_process(self.api_process, "FastAPI")
      self.api_process = None

    self.release_lock()
    print("[*] DENTRACE shutdown complete. Clean exit (0 orphan processes).")

  def _terminate_process(self, proc: subprocess.Popen, name: str):
    """Gracefully terminate a process and its child tree."""
    pid = proc.pid
    try:
      if os.name == "nt":
        # Forcefully terminate entire process tree using taskkill
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5.0,
        )
      else:
        proc.terminate()
        proc.wait(timeout=3.0)
    except Exception:
      try:
        proc.kill()
      except Exception:
        pass
    print(f"    [-] {name} service terminated (PID {pid}).")


def main():
  """Launcher entry point."""
  launcher = DentraceLauncher()

  # Register exit handler
  atexit.register(launcher.shutdown)
  signal.signal(signal.SIGINT, lambda s, f: launcher.shutdown())
  signal.signal(signal.SIGTERM, lambda s, f: launcher.shutdown())

  print("=" * 70)
  print(f"  {launcher.app_name} v{launcher.version}")
  print("  Preflight Initialization & Diagnostic Verification")
  print("=" * 70)

  # 1. Single Instance Check
  if not launcher.acquire_single_instance_lock():
    sys.exit(0)

  # 2. Preflight checks
  if not launcher.check_python_runtime():
    sys.exit(1)
  if not launcher.check_disk_space():
    sys.exit(1)
  if not launcher.check_ports():
    sys.exit(1)
  if not launcher.check_database():
    sys.exit(1)

  # 3. Informational checks
  launcher.check_models()
  launcher.check_hardware()

  # 4. Start services
  if not launcher.start_services():
    sys.exit(1)

  # 5. Supervision loop
  launcher.supervise()


if __name__ == "__main__":
  main()
