test:
	docker-compose exec dev python -m pytest -s -v

.PHONY: test