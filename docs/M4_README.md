# M4 Operator Prototype

M4 adds the human control plane and ground-truth collection loop.

## Operator views

- Pricing Overview
- Mapping Review
- Price Review
- Evaluation
- Audit

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
streamlit run ui/streamlit_app.py
```

The database is local SQLite and should not be committed.
