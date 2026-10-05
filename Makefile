.PHONY: up demo load test down logs

up:
	docker compose up -d --build

demo: up
	DATA_FILE=data/sample.csv docker compose run --rm loader

load:
	docker compose run --rm loader

test:
	docker compose run --rm tests

logs:
	docker compose logs -f app

down:
	docker compose down
