CONTAINER_IMAGE=$(shell bash scripts/container_image.sh)
PYTHON ?= "python3"
PYTEST_OPTS ?= "-s -vvv"
PYTEST_DIR ?= "tests"
ABACO_DEPLOY_OPTS ?= "-p"
SCRIPT_DIR ?= "scripts"
PREF_SHELL ?= "bash"
ACTOR_ID ?=
NOCLEANUP ?= 0

GITREF=$(shell git rev-parse --short HEAD)

.PHONY: tests container tests-local tests-reactor tests-deployed datacatalog formats
.SILENT: tests container tests-local tests-reactor tests-deployed datacatalog formats shell

all: image

image:
	abaco deploy -R -F Dockerfile -k -B reactor.rc -R -t $(GITREF) $(ABACO_DEPLOY_OPTS)

shell:
	bash $(SCRIPT_DIR)/run_container_process.sh bash

tests: tests-local

tests-pytest:
	bash $(SCRIPT_DIR)/run_container_process.sh $(PYTHON) -m "pytest" $(PYTEST_DIR) $(PYTEST_OPTS)

tests-local: tests-local-biofab tests-local-transcriptic tests-local-ginkgo

tests-local-biofab:
	bash $(SCRIPT_DIR)/run_container_message.sh tests/data/local-message-01-biofab.json

tests-local-transcriptic:
	bash $(SCRIPT_DIR)/run_container_message.sh tests/data/local-message-01-transcriptic.json

tests-local-ginkgo:
	bash $(SCRIPT_DIR)/run_container_message.sh tests/data/local-message-01-ginkgo.json

tests-deployed:
	echo "not implemented"

clean: clean-image clean-tests

clean-image:
	docker rmi -f $(CONTAINER_IMAGE)

clean-tests:
	rm -rf .hypothesis .pytest_cache __pycache__ */__pycache__ tmp.* *junit.xml

deploy:
	abaco deploy -F Dockerfile -B reactor.rc -t $(GITREF) $(ABACO_DEPLOY_OPTS) -U $(ACTOR_ID)

postdeploy:
	bash tests/run_after_deploy.sh

samples:
	cp ../etl-pipeline-support/output/ginkgo/Novelchassis_Nand_gate_samples.json tests/data/samples-ginkgo.json
	cp ../etl-pipeline-support/output/biofab/provenance_dump.json tests/data/samples-biofab.json
	cp ../etl-pipeline-support/output/transcriptic/samples.json tests/data/samples-transcriptic.json
