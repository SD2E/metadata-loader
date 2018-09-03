CONTAINER_IMAGE=$(shell bash scripts/container_image.sh)
PYTHON ?= "python3"
PYTEST_OPTS ?= "-s -vvv"
PYTEST_DIR ?= "tests"
ABACO_DEPLOY_OPTS ?= "-p"
SCRIPT_DIR ?= "scripts"
PREF_SHELL ?= "bash"
ACTOR_ID ?=

.PHONY: tests container tests-local tests-reactor tests-deployed datacatalog formats
.SILENT: tests container tests-local tests-reactor tests-deployed datacatalog formats

all: image

formats:
	if [ -d ../etl-pipeline-support/formats ]; then rm -rf formats; cp -R ../etl-pipeline-support/formats .; fi

datacatalog: formats
	if [ -d ../datacatalog ]; then rm -rf datacatalog; cp -R ../datacatalog .; fi

image: datacatalog
	abaco deploy -R $(ABACO_DEPLOY_OPTS)

shell:
	bash $(SCRIPT_DIR)/run_container_process.sh bash

tests: tests-pytest tests-local

tests-pytest:
	bash $(SCRIPT_DIR)/run_container_process.sh $(PYTHON) -m "pytest" $(PYTEST_DIR) $(PYTEST_OPTS)

tests-local:
	bash $(SCRIPT_DIR)/run_container_message.sh tests/data/local-message-01.json

tests-deployed:
	echo "not implemented"

clean: clean-image clean-tests

clean-image:
	docker rmi -f $(CONTAINER_IMAGE)

clean-tests:
	rm -rf .hypothesis .pytest_cache __pycache__ */__pycache__ tmp.* *junit.xml

deploy:
	abaco deploy $(ABACO_DEPLOY_OPTS) -U $(ACTOR_ID)

postdeploy:
	bash tests/run_after_deploy.sh
