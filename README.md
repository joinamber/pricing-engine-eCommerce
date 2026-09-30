# Competitive Pricing Engine

MVP for iStudio Singapore competitive pricing. The repository implements the deterministic M1 baseline, COURTS Singapore M2 adapter boundary, M3 identity mapping, M3.2 structured retrieval, and M4 operator/review workflow.

## Current milestone
M4 operator prototype.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
streamlit run ui/streamlit_app.py
```

Open http://localhost:8501.

## Safety boundary

Model/shadow mapping is advisory. Only exact trusted identifiers are auto-eligible in the prototype. Production publication is not connected; publication in M4 is a mock operation.

## Architecture

```text
COURTS observation -> extraction -> normalization -> identity mapping -> market price -> pricing policy -> review -> mock publish -> audit
```

See `docs/` for the product/engineering manual, mapping concepts, and milestone reports.
