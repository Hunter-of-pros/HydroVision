.PHONY: help setup test mock-backend real-backend fixtures smoke clean frontend-install frontend-dev frontend-build

help:
	@echo "HydroVision Development Tasks"
	@echo "  make setup            Install project dependencies via pip"
	@echo "  make test             Run pytest suite (runs real tests + xfails stubs)"
	@echo "  make mock-backend     Start FastAPI server in mock mode (port 8000)"
	@echo "  make real-backend     Start FastAPI server with real ML models"
	@echo "  make fixtures         Generate static fixtures in fixtures/ from mock"
	@echo "  make smoke            Run backend smoke test against all endpoints"
	@echo "  make frontend-install Install frontend dependencies via npm"
	@echo "  make frontend-dev     Start React + Vite frontend development server"
	@echo "  make frontend-build   Build production frontend bundle"
	@echo "  make clean            Remove cached build artifacts and temporary files"

setup:
	pip install -r requirements.txt

test:
	pytest -v

mock-backend:
	HYDRO_MODE=mock uvicorn backend.app:app --reload --port 8000

real-backend:
	HYDRO_MODE=real uvicorn backend.app:app --reload --port 8000

fixtures:
	python scripts/make_fixtures.py

smoke:
	python scripts/smoke_test.py

frontend-install:
	npm install --prefix frontend

frontend-dev:
	npm run dev --prefix frontend

frontend-build:
	npm run build --prefix frontend

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.py[co]" -delete
	rm -rf .coverage htmlcov

