.PHONY: dev backend frontend build clean

VENV = .venv
PY = $(VENV)/bin/python
UVICORN = $(VENV)/bin/uvicorn

dev: backend frontend		# run "make dev"

backend:
	@echo "Starting backend development server..."
	$(UVICORN) backend.app.main:app --reload &

frontend:
	pnpm --prefix frontend dev &

build:
	pnpm --prefix frontend build

clean:
	-pkill -f "uvicorn.*backend.app.main" || true
	-pkill -f "vite" || true

	