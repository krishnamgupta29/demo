import onnxruntime as ort
from pathlib import Path

def inspect_model(model_path: Path):
    print("=" * 60)
    print(f"Inspecting: {model_path.name}")
    print(f"File path: {model_path}")
    print(f"Size: {model_path.stat().st_size} bytes")

    # Load with onnxruntime
    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    meta = session.get_modelmeta()
    print(f"Producer: {meta.producer_name} {meta.version}")
    print(f"Description: {meta.description}")
    print("Custom Metadata Map:")
    for k, v in meta.custom_metadata_map.items():
        print(f"  {k}: {v[:100] if len(v) > 100 else v}")

    # Load with onnxruntime
    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    print("\nInputs:")
    for inp in session.get_inputs():
        print(f"  Name: {inp.name}, Shape: {inp.shape}, Type: {inp.type}")
    print("\nOutputs:")
    for out in session.get_outputs():
        print(f"  Name: {out.name}, Shape: {out.shape}, Type: {out.type}")

def main():
    checkpoints = [
        Path("C:/mini/models/checkpoints/best.onnx"),
        Path("C:/mini/models/checkpoints/dental_fdi.onnx"),
    ]
    for cp in checkpoints:
        if cp.exists():
            inspect_model(cp)
        else:
            print(f"Model not found: {cp}")

if __name__ == "__main__":
    main()
