"""Dependency installation verification script for DENTRACE.

Run after fresh venv creation:
    py -3.11 -m venv C:\\mini\\.venv
    C:\\mini\\.venv\\Scripts\\pip install -r requirements.txt
    C:\\mini\\.venv\\Scripts\\python scripts\\verify_dependencies.py
"""
import sys
import importlib.metadata as meta

print(f"Python: {sys.version}")

EXPECTED = {
    "pillow": {
        "import": "PIL",
        "attr": "__version__",
        "min": (10, 2, 0),
        "test": lambda: __import__("PIL.Image", fromlist=["Image"]).Image.new("L", (10, 10)),
        "test_desc": "Image.new('L', (10,10))",
    },
    "numpy": {
        "import": "numpy",
        "attr": "__version__",
        "min": (1, 24, 0),
        "test": lambda: __import__("numpy").zeros((1, 3, 640, 640), dtype=__import__("numpy").float32),
        "test_desc": "np.zeros((1,3,640,640), float32)",
    },
    "onnxruntime": {
        "import": "onnxruntime",
        "attr": "__version__",
        "min": (1, 18, 0),
        "test": lambda: __import__("onnxruntime").get_available_providers(),
        "test_desc": "get_available_providers()",
    },
    "fastapi": {
        "import": "fastapi",
        "attr": "__version__",
        "min": (0, 115, 0),
        "test": lambda: __import__("fastapi").FastAPI(),
        "test_desc": "FastAPI()",
    },
    "sqlalchemy": {
        "import": "sqlalchemy",
        "attr": "__version__",
        "min": (2, 0, 0),
        "test": lambda: __import__("sqlalchemy").create_engine("sqlite:///:memory:"),
        "test_desc": "create_engine sqlite",
    },
    "streamlit": {
        "import": "streamlit",
        "attr": "__version__",
        "min": (1, 38, 0),
        "test": None,
        "test_desc": "import only",
    },
    "reportlab": {
        "import": "reportlab",
        "attr": "Version",
        "min": (4, 2, 0),
        "test": lambda: __import__("reportlab.pdfgen.canvas", fromlist=["canvas"]).canvas.Canvas,
        "test_desc": "canvas.Canvas",
    },
}

all_ok = True
print("\n{:<20} {:<15} {:<10} {:<30}".format("Package", "Installed", "Min", "Test"))
print("-" * 80)
for pkg, cfg in EXPECTED.items():
    try:
        version_str = meta.version(pkg)
        vt = tuple(int(x) for x in version_str.split(".")[:3])
        ok = vt >= cfg["min"]
        if not ok:
            all_ok = False

        test_result = "N/A"
        if cfg.get("test"):
            try:
                cfg["test"]()
                test_result = "PASS"
            except Exception as e:
                test_result = f"FAIL: {e}"
                all_ok = False
        else:
            try:
                __import__(cfg["import"])
                test_result = "import OK"
            except Exception as e:
                test_result = f"FAIL: {e}"
                all_ok = False

        status = "OK  " if ok else "WARN"
        print(f"[{status}] {pkg:<18} {version_str:<15} >={'.'.join(map(str,cfg['min'])):<10} {cfg['test_desc']:<25} {test_result}")
    except meta.PackageNotFoundError:
        print(f"[MISS] {pkg:<18} NOT INSTALLED")
        all_ok = False

print()
if all_ok:
    print("All dependency checks PASSED. Environment is ready.")
    sys.exit(0)
else:
    print("FAILED — see issues above. Run: pip install -r requirements.txt")
    sys.exit(1)
