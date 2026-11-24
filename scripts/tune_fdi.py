import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.benchmark_fdi_calibration import load_dentex_enumeration_data, CalibratedFDISolver, evaluate_solver

test_files, anns_by_file, file_to_info = load_dentex_enumeration_data(num_images=150)
best_acc = 0
best_params = None
for gap in [1.35, 1.45, 1.50, 1.55, 1.60, 1.65, 1.70, 1.75]:
    for mid in [1.10, 1.25, 1.35, 1.50, 1.75, 2.0, 2.2]:
        solver = CalibratedFDISolver(gap_pitch_ratio_threshold=gap, midline_gap_ratio=mid)
        res = evaluate_solver(solver, test_files, anns_by_file, file_to_info)
        acc = res["overall_exact_fdi_accuracy"]
        if acc > best_acc:
            best_acc = acc
            best_params = (gap, mid)
            print(f"New Best: gap={gap}, mid={mid} -> Acc: {best_acc}%, Non-abstained: {res['effective_precision_non_abstained']}%, Abst: {res['abstention_rate']}%, Quad: {res['quadrant_accuracy']}%")

print(f"Optimal configuration: {best_params} with accuracy {best_acc}%")
