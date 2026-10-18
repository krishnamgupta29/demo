# AGENTS.md — Guidance for Autonomous & Collaborative AI Engineers

## 1. Project Mission & Identity
- **Project Name:** DENTRACE
- **Domain:** Local-first dental panoramic radiograph (OPG) anomaly detection and insurance claim pre-authorization engine.
- **Type:** Academic college decision-support system.
- **Legal & Regulatory Boundary:** **"Draft for dentist review. Not a diagnosis."** Not a certified medical device (FDA/CE/MDR). Must never claim autonomous clinical diagnosis, treatment determination, or automated insurance approval.

---

## 2. Environment & Host Machine Directives
- **Python Version:** Use **Python 3.11.9** (`py -3.11`). Do NOT use Python 3.13 or 3.15 for project execution.
- **Disk Budget Constraint:**
  - `C:\` has ~150 GB free (use for dataset staging, pip caches, Ollama models).
  - `D:\` has only **~4.58 GB free**. **NEVER download large datasets or model checkpoints to D:.**
- **GPU Hardware:** NVIDIA GeForce RTX 2050 (4 GB VRAM). Training must be batch-constrained ($B \le 8$) or offloaded to Google Colab T4.
- **Local LLM:** Ollama 0.40.6 running locally at `127.0.0.1:11434`.

---

## 3. Strict Engineering & Quality Rules
1. **Never Invent Results:** Do not write fake accuracy or benchmark metrics. If an evaluation cannot be run, mark as `PENDING` or `UNVERIFIED`.
2. **Never Falsify Segmentation:** Distinguish true instance segmentation polygons from bounding-box detection fallbacks. Never present a bounding box as a pixel mask.
3. **Separation of Clinical Facts:** The deterministic rule layer is strictly authoritative for tooth assignment, condition taxonomy, and urgency categorization. The downstream language model is only permitted to rewrite verified facts under a strict Pydantic JSON schema format constraint.
4. **Zero Cloud Egress:** All inference, image analysis, and LLM drafting must run strictly offline on localhost.
5. **Level-Based Progression:** Respect the phased level progression (Level 0 through Level 10). Do not jump to training or UI construction without explicit gate approval.
