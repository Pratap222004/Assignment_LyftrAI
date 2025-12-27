.PHONY: help build up down logs test clean

help:
	@echo "Available commands:"
	@echo "  make build  - Build Docker image"
	@echo "  make up     - Start services"
	@echo "  make down   - Stop services"
	@echo "  make logs   - Show logs"
	@echo "  make test   - Run tests"
	@echo "  make clean  - Clean up data and containers"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f api

test:
	docker compose exec -e WEBHOOK_SECRET=testsecret api pytest tests/ -v


clean:
	docker compose down -v
	rm -rf data/
