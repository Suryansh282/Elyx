# Backend — Member Journey & Reasoning API

## Quick start

```bash
cd backend
python -m venv .venv
. .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env
python -m app.ingest  # creates app.db and seeds sample data
uvicorn app.main:app --reload
