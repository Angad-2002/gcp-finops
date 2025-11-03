.PHONY: help build up down shell cli api clean logs

# Default target
help:
	@echo "GCP FinOps Dashboard - Docker Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start CLI in interactive mode"
	@echo "  make down           - Stop and remove containers"
	@echo "  make shell          - Open shell in CLI container"
	@echo "  make cli            - Run CLI interactively"
	@echo "  make api            - Start API server"
	@echo "  make clean          - Clean up containers and volumes"
	@echo "  make logs           - View container logs"
	@echo "  make dashboard      - Run dashboard command"
	@echo "  make audit          - Run audit command"
	@echo "  make forecast       - Run forecast command"
	@echo ""

# Build Docker images
build:
	docker-compose build

# Start CLI interactively
up:
	docker-compose up cli

# Start CLI in background
up-d:
	docker-compose up -d cli

# Stop containers
down:
	docker-compose down

# Open shell in container
shell:
	docker-compose run --rm cli /bin/bash

# Run interactive CLI
cli:
	docker-compose run --rm cli gcp-finops setup --interactive

# Start API server
api:
	docker-compose --profile api up api

# Clean up everything
clean:
	docker-compose down -v --rmi local
	@echo "Cleaned up containers, volumes, and images"

# View logs
logs:
	docker-compose logs -f cli

# Run dashboard command (requires GCP_BILLING_DATASET env var)
dashboard:
	@if [ -z "$(GCP_BILLING_DATASET)" ]; then \
		echo "Error: GCP_BILLING_DATASET environment variable not set"; \
		exit 1; \
	fi
	docker-compose run --rm cli gcp-finops dashboard \
		--billing-dataset $(GCP_BILLING_DATASET)

# Run audit command
audit:
	@if [ -z "$(GCP_BILLING_DATASET)" ]; then \
		echo "Error: GCP_BILLING_DATASET environment variable not set"; \
		exit 1; \
	fi
	@if [ -z "$(AUDIT_TYPE)" ]; then \
		echo "Error: AUDIT_TYPE not set (e.g., cloud-run, functions, compute)"; \
		exit 1; \
	fi
	docker-compose run --rm cli gcp-finops audit $(AUDIT_TYPE) \
		--billing-dataset $(GCP_BILLING_DATASET)

# Run forecast command
forecast:
	@if [ -z "$(GCP_BILLING_DATASET)" ]; then \
		echo "Error: GCP_BILLING_DATASET environment variable not set"; \
		exit 1; \
	fi
	docker-compose run --rm cli gcp-finops forecast \
		--billing-dataset $(GCP_BILLING_DATASET)

# Rebuild without cache
rebuild:
	docker-compose build --no-cache

# Check container status
status:
	docker-compose ps

# Execute arbitrary command in container
exec:
	docker-compose run --rm cli $(CMD)

