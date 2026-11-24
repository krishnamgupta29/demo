"""Benchmark end-to-end timing across the 3 sample OPGs in samples/."""

import time
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.main import app

def benchmark_sample(client: TestClient, img_path: Path):
    print(f"\n--- Benchmarking {img_path.name} ---")
    filename = img_path.name
    
    # 1. Upload & Intake
    with open(img_path, 'rb') as f:
        t0 = time.perf_counter()
        resp = client.post('/api/v1/studies/upload', files={'file': (filename, f, 'image/png')})
        t_upload_ms = (time.perf_counter() - t0) * 1000.0
    
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    study_id = resp.json()['study_id']
    print(f"  Uploaded study_id: {study_id} in {t_upload_ms:.1f} ms")
    
    # 2. Radiograph Analysis (Pathology Detection + FDI Localization)
    t0 = time.perf_counter()
    resp_an = client.post(f'/api/v1/studies/{study_id}/analyze')
    t_analysis_ms = (time.perf_counter() - t0) * 1000.0
    assert resp_an.status_code == 200, f"Analysis failed: {resp_an.text}"
    findings_count = len(resp_an.json().get('findings', []))
    print(f"  Analysis completed: {findings_count} findings in {t_analysis_ms:.1f} ms")
    
    # 3. Local Narrative Synthesis (CPU Ollama qwen2.5:3b)
    t0 = time.perf_counter()
    resp_dr = client.post(f'/api/v1/insurance/studies/{study_id}/draft')
    t_narrative_ms = (time.perf_counter() - t0) * 1000.0
    assert resp_dr.status_code == 200, f"Draft failed: {resp_dr.text}"
    draft_data = resp_dr.json()
    engine_used = draft_data.get('meta', {}).get('engine', 'unknown')
    print(f"  Narrative completed: engine={engine_used} in {t_narrative_ms:.1f} ms")
    
    # 4. Claim Pack PDF Export
    t0 = time.perf_counter()
    resp_pdf = client.get(f'/api/v1/insurance/studies/{study_id}/claim-pack/pdf')
    t_pdf_ms = (time.perf_counter() - t0) * 1000.0
    assert resp_pdf.status_code == 200, f"PDF failed: {resp_pdf.text}"
    pdf_bytes = len(resp_pdf.content)
    print(f"  PDF generated: {pdf_bytes} bytes in {t_pdf_ms:.1f} ms")
    
    total_ms = t_upload_ms + t_analysis_ms + t_narrative_ms + t_pdf_ms
    return {
        "filename": filename,
        "study_id": study_id,
        "findings_count": findings_count,
        "upload_ms": round(t_upload_ms, 2),
        "analysis_ms": round(t_analysis_ms, 2),
        "narrative_ms": round(t_narrative_ms, 2),
        "pdf_ms": round(t_pdf_ms, 2),
        "total_ms": round(total_ms, 2),
        "pdf_bytes": pdf_bytes,
        "engine": engine_used
    }

def main():
    client = TestClient(app)
    samples_dir = Path("samples")
    sample_files = ["sample_opg_1.png", "sample_opg_2.png", "sample_opg_3.png"]
    
    results = []
    for sname in sample_files:
        spath = samples_dir / sname
        if spath.exists():
            res = benchmark_sample(client, spath)
            results.append(res)
    
    out_path = Path("scratch/task_g2_timings.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nAll 3 samples completed. Saved to {out_path}")

if __name__ == "__main__":
    main()
