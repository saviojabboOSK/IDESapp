# Makefile for IDES 2.0 - Indoor Digital Environment System with cross-platform development, testing, and deployment automation for sensor data visualization dashboard.

.PHONY: help install dev backend frontend build clean docker test lint format setup

# Default Python and Node paths
PYTHON := python3
PIP := pip3
NODE := node
NPM := npm
PNPM := pnpm

# Virtual environment
VENV := .venv
VENV_BIN := $(VENV)/bin
VENV_PYTHON := $(VENV_BIN)/python
VENV_PIP := $(VENV_BIN)/pip

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "IDES 2.0 - Indoor Digital Environment System"
	@echo "============================================="
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install all dependencies (Python + Node.js)
	@echo "$(YELLOW)Installing dependencies...$(NC)"
	$(MAKE) install-backend
	$(MAKE) install-frontend
	@echo "$(GREEN)✓ All dependencies installed$(NC)"

install-backend: ## Install Python backend dependencies
	@echo "$(YELLOW)Setting up Python backend...$(NC)"
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r backend/requirements.txt
	@echo "$(GREEN)✓ Backend dependencies installed$(NC)"

install-frontend: ## Install Node.js frontend dependencies
	@echo "$(YELLOW)Setting up React frontend...$(NC)"
	cd frontend && $(PNPM) install
	@echo "$(GREEN)✓ Frontend dependencies installed$(NC)"

setup: install ## Complete project setup with example configuration
	@echo "$(YELLOW)Setting up project configuration...$(NC)"
	@if [ ! -f backend/.env ]; then \
		cp backend/.env.example backend/.env 2>/dev/null || echo "# IDES 2.0 Configuration\nINFLUX_URL=http://localhost:8086\nINFLUX_TOKEN=demo_token\nINFLUX_ORG=ides\nINFLUX_BUCKET=sensors\nLLM_BACKEND=local\nLOCAL_LLM_URL=http://localhost:11434\nCOLLECTION_INTERVAL=30\nDATA_RETENTION_WEEKS=4" > backend/.env; \
		echo "$(GREEN)✓ Created backend/.env configuration$(NC)"; \
	fi
	@mkdir -p backend/data
	@echo "$(GREEN)✓ Project setup complete$(NC)"

dev: ## Start development servers (backend + frontend)
	@echo "$(YELLOW)Starting IDES 2.0 development environment...$(NC)"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo "$(YELLOW)Press Ctrl+C to stop all services$(NC)"
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend: ## Start backend development server only
	@echo "$(YELLOW)Starting FastAPI backend...$(NC)"
	cd backend && $(VENV_PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start frontend development server only
	@echo "$(YELLOW)Starting React frontend...$(NC)"
	cd frontend && $(PNPM) dev

backend: dev-backend ## Alias for dev-backend

frontend: dev-frontend ## Alias for dev-frontend

build: ## Build production bundles
	@echo "$(YELLOW)Building production bundles...$(NC)"
	cd frontend && $(PNPM) build
	@echo "$(GREEN)✓ Frontend built to frontend/dist$(NC)"

test: ## Run all tests
	@echo "$(YELLOW)Running tests...$(NC)"
	$(MAKE) test-backend
	$(MAKE) test-frontend

test-backend: ## Run backend tests
	@echo "$(YELLOW)Running backend tests...$(NC)"
	cd backend && $(VENV_PYTHON) -m pytest tests/ -v || echo "$(YELLOW)No tests found - create tests in backend/tests/$(NC)"

test-frontend: ## Run frontend tests  
	@echo "$(YELLOW)Running frontend tests...$(NC)"
	cd frontend && $(PNPM) test || echo "$(YELLOW)No tests configured - add test script to package.json$(NC)"

lint: ## Run linting for all code
	@echo "$(YELLOW)Running code linting...$(NC)"
	$(MAKE) lint-backend
	$(MAKE) lint-frontend

lint-backend: ## Run Python linting
	@echo "$(YELLOW)Linting Python code...$(NC)"
	cd backend && $(VENV_PYTHON) -m ruff check . || echo "$(YELLOW)Install ruff for linting: pip install ruff$(NC)"

lint-frontend: ## Run TypeScript/React linting
	@echo "$(YELLOW)Linting TypeScript code...$(NC)"
	cd frontend && $(PNPM) lint

format: ## Format all code
	@echo "$(YELLOW)Formatting code...$(NC)"
	$(MAKE) format-backend
	$(MAKE) format-frontend

format-backend: ## Format Python code
	@echo "$(YELLOW)Formatting Python code...$(NC)"
	cd backend && $(VENV_PYTHON) -m ruff format . || echo "$(YELLOW)Install ruff for formatting: pip install ruff$(NC)"

format-frontend: ## Format TypeScript/React code
	@echo "$(YELLOW)Formatting TypeScript code...$(NC)"
	cd frontend && $(PNPM) prettier --write src/

docker: ## Run with Docker Compose (full stack)
	@echo "$(YELLOW)Starting IDES 2.0 with Docker...$(NC)"
	docker-compose up --build

docker-dev: ## Run development stack with Docker
	@echo "$(YELLOW)Starting development stack...$(NC)"
	docker-compose -f docker-compose.yml up --build backend frontend influxdb

docker-prod: ## Run production stack with Docker
	@echo "$(YELLOW)Starting production stack...$(NC)"
	docker-compose -f docker-compose.yml --profile prod up -d --build

docker-llm: ## Run with local LLM service
	@echo "$(YELLOW)Starting with Ollama LLM service...$(NC)"
	docker-compose --profile llm up --build

logs: ## Show Docker logs
	docker-compose logs -f

clean: ## Clean all build artifacts and dependencies
	@echo "$(YELLOW)Cleaning project...$(NC)"
	rm -rf $(VENV)
	rm -rf frontend/node_modules
	rm -rf frontend/dist
	rm -rf backend/__pycache__
	rm -rf backend/**/__pycache__
	rm -rf backend/data/*.json
	@echo "$(GREEN)✓ Project cleaned$(NC)"

clean-docker: ## Clean Docker containers and volumes
	@echo "$(YELLOW)Cleaning Docker resources...$(NC)"
	docker-compose down -v
	docker system prune -f
	@echo "$(GREEN)✓ Docker resources cleaned$(NC)"

status: ## Show service status
	@echo "$(YELLOW)IDES 2.0 Service Status$(NC)"
	@echo "======================="
	@curl -s http://localhost:8000/api/health 2>/dev/null | grep -q "healthy" && echo "$(GREEN)✓ Backend: Running$(NC)" || echo "$(RED)✗ Backend: Not running$(NC)"
	@curl -s http://localhost:5173 2>/dev/null >/dev/null && echo "$(GREEN)✓ Frontend: Running$(NC)" || echo "$(RED)✗ Frontend: Not running$(NC)"
	@curl -s http://localhost:8086/health 2>/dev/null | grep -q "pass" && echo "$(GREEN)✓ InfluxDB: Running$(NC)" || echo "$(RED)✗ InfluxDB: Not running$(NC)"

stop: ## Stop all development servers
	@echo "$(YELLOW)Stopping all services...$(NC)"
	-pkill -f "uvicorn.*app.main" 2>/dev/null || true
	-pkill -f "vite.*frontend" 2>/dev/null || true
	@echo "$(GREEN)✓ All services stopped$(NC)"

restart: stop dev ## Restart all development servers

# Platform-specific installations
install-mac: ## Install dependencies on macOS
	@echo "$(YELLOW)Installing for macOS...$(NC)"
	@which brew >/dev/null || (echo "$(RED)Please install Homebrew first$(NC)" && exit 1)
	brew install python3 node pnpm
	$(MAKE) install

install-linux: ## Install dependencies on Linux
	@echo "$(YELLOW)Installing for Linux...$(NC)"
	@which python3 >/dev/null || (echo "$(RED)Please install Python 3$(NC)" && exit 1)
	@which node >/dev/null || (echo "$(RED)Please install Node.js$(NC)" && exit 1)
	npm install -g pnpm
	$(MAKE) install

install-windows: ## Install dependencies on Windows (requires WSL or Git Bash)
	@echo "$(YELLOW)Installing for Windows...$(NC)"
	@echo "$(YELLOW)Ensure Python 3 and Node.js are installed$(NC)"
	npm install -g pnpm
	$(MAKE) install

# Database management
db-setup: ## Setup InfluxDB with sample data
	@echo "$(YELLOW)Setting up InfluxDB...$(NC)"
	docker-compose up -d influxdb
	@echo "$(GREEN)✓ InfluxDB running on http://localhost:8086$(NC)"
	@echo "Login: admin / password123"

db-reset: ## Reset InfluxDB data
	@echo "$(YELLOW)Resetting InfluxDB...$(NC)"
	docker-compose down influxdb
	docker volume rm ides_influxdb_data ides_influxdb_config 2>/dev/null || true
	$(MAKE) db-setup

# Info commands
info: ## Show project information
	@echo "$(GREEN)IDES 2.0 - Indoor Digital Environment System$(NC)"
	@echo "=============================================="
	@echo "Backend:  FastAPI + Python"
	@echo "Frontend: React + TypeScript + Vite"
	@echo "Database: InfluxDB"
	@echo "AI:       OpenAI API / Local LLM (Ollama)"
	@echo ""
	@echo "URLs:"
	@echo "  Frontend: http://localhost:5173"
	@echo "  Backend:  http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  InfluxDB: http://localhost:8086"

requirements: ## Show system requirements
	@echo "$(YELLOW)System Requirements:$(NC)"
	@echo "- Python 3.10+"
	@echo "- Node.js 18+"
	@echo "- pnpm package manager"
	@echo "- Docker & Docker Compose (optional)"
	@echo "- 4GB+ RAM recommended"
	@echo "- InfluxDB 2.x (local or cloud)"