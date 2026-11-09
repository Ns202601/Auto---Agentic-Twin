PY := .venv/bin/python

.PHONY: setup compile check process artifact test all clean serve ui ui-dev

setup:          ## create .venv and install the package + pytest
	./scripts/setup_env.sh

compile:        ## byte-compile all Python code (syntax check)
	$(PY) -m cvtwin compile

check:          ## validate research data -> artifacts/data_check_report.{md,json}
	$(PY) -m cvtwin check

process:        ## build clean tables -> artifacts/processed/*.csv
	$(PY) -m cvtwin process

artifact:       ## build the Data Lab page -> artifacts/data_lab.html
	$(PY) -m cvtwin artifact

test:           ## run unit tests
	$(PY) -m pytest -q

serve:          ## run the orchestrator API + built UI on http://127.0.0.1:8000
	$(PY) -m twinorch serve

ui:             ## build the UI into ui/dist (served by `make serve`)
	cd ui && npm install --no-audit --no-fund && npm run build

ui-dev:         ## hot-reloading UI on :5173 (run `make serve` in another terminal)
	cd ui && npm run dev

all: compile test check process artifact

clean:
	rm -rf ui/node_modules ui/dist var
	rm -rf .venv .pytest_cache build *.egg-info src/*.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
