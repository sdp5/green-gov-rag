setup:
	cd deploy/aws && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

deploy-aws:
	cd deploy/aws && source .venv/bin/activate && cdk deploy

ingest:
	python scripts/ingest_docs.py

run:
	uvicorn app.main:app --reload
