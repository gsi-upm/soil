quick-test:
	docker-compose exec dev python -m pytest -s -v

test:
	docker run -t -v $$PWD:/usr/src/app -w /usr/src/app python:3.7 python setup.py test

.PHONY: test
