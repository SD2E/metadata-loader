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

SD2_ACTOR_ID ?= YVqpm0zYz6YYD
BIOCON_ACTOR_ID ?= 3JyWwYAzNOlXP
SAFEGENES_ACTOR_ID ?= RyZO30A607gV

.PHONY: tests container tests-local tests-reactor tests-deployed datacatalog formats
.SILENT: tests container tests-local tests-reactor tests-deployed datacatalog formats shell

all: image

image: image-sd2 image-biocon image-safegenes

image-sd2:
	abaco deploy -k -R -F Dockerfile -c sd2_metadata_loader -t $(GITREF) $(ABACO_DEPLOY_OPTS)

image-biocon:
	abaco deploy -k -R -F Dockerfile.biocon -c biocon_metadata_loader -t $(GITREF) $(ABACO_DEPLOY_OPTS)

image-safegenes:
	abaco deploy -k -R -F Dockerfile.safegenes -c safegenes_metadata_loader -t $(GITREF) $(ABACO_DEPLOY_OPTS)

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

clean-image: clean-sd2 clean-biocon clean-safegenes

clean-sd2:
	docker rmi -f sd2e/sd2_metadata_loader:$(GITREF)

clean-biocon:
	docker rmi -f sd2e/biocon_metadata_loader:$(GITREF)

clean-safegenes:
	docker rmi -f sd2e/safegenes_metadata_loader:$(GITREF)

clean-tests:
	rm -rf .hypothesis .pytest_cache __pycache__ */__pycache__ tmp.* *junit.xml

deploy: deploy-sd2 deploy-biocon deploy-safegenes

deploy-sd2:
	abaco deploy -F Dockerfile.sd2 -c sd2_metadata_loader -t $(GITREF) $(ABACO_DEPLOY_OPTS) -U $(SD2_ACTOR_ID)

deploy-biocon:
	abaco deploy -F Dockerfile.biocon -c biocon_metadata_loader -t $(GITREF) $(ABACO_DEPLOY_OPTS) -U $(BIOCON_ACTOR_ID)

deploy-safegenes:
	abaco deploy -F Dockerfile.safegenes -c safegenes_metadata_loader -t $(GITREF) $(ABACO_DEPLOY_OPTS) -U $(SAFEGENES_ACTOR_ID)

postdeploy:
	bash tests/run_after_deploy.sh

samples:
	cp ../etl-pipeline-support/output/ginkgo/Novelchassis_Nand_gate_samples.json tests/data/samples-ginkgo.json
	cp ../etl-pipeline-support/output/biofab/provenance_dump.json tests/data/samples-biofab.json
	cp ../etl-pipeline-support/output/transcriptic/samples.json tests/data/samples-transcriptic.json
