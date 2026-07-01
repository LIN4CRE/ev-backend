.PHONY: test lint typecheck check alexa-validate alexa-generate alexa-endpoint alexa-sync alexa-ready alexa-local-dev doctor

test:
	pytest -q

lint:
	ruff check .

typecheck:
	mypy app

doctor:
	python scripts/doctor.py

alexa-generate:
	python scripts/generate_alexa_skill_package.py

alexa-endpoint:
	python scripts/update_alexa_endpoint.py

alexa-sync:
	python scripts/sync_alexa_tunnel.py

alexa-ready: alexa-generate alexa-sync alexa-validate

alexa-local-dev:
	python scripts/alexa_local_dev.py

alexa-validate:
	python scripts/validate_alexa_skill_package.py

check: lint typecheck alexa-generate alexa-endpoint alexa-validate test
