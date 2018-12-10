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

formats:
	if [ -d ../etl-pipeline-support/formats ]; then rm -rf formats; cp -R ../etl-pipeline-support/formats .; fi

datacatalog: formats
	if [ -d ../python-datacatalog/datacatalog ]; then rm -rf datacatalog; cp -R ../python-datacatalog/datacatalog .; fi

image: config-prod image-prod

config-init:
	if [ -f config.yml ]; then cp config.yml config-prod.yml; fi
	if [ -f config.yml ]; then cp config.yml config-staging.yml; fi

config-prod:
	cp config-prod.yml config.yml

config-staging:
	cp config-staging.yml config.yml

secrets-init:
	if [ -f secrets.json ]; then cp secrets.json secrets-prod.json; fi
	if [ -f secrets.json ]; then cp secrets.json secrets-staging.json; fi

secrets-prod:
	cp secrets-prod.json secrets.json

secrets-staging:
	cp secrets-staging.json secrets.json

image-prod: config-prod secrets-prod
	abaco deploy -F Dockerfile -k -B reactor.rc -R -t $(GITREF) $(ABACO_DEPLOY_OPTS)

image-staging: config-staging secrets-staging
	abaco deploy -F Dockerfile.staging -k -B reactor-staging.rc -R -t $(GITREF) $(ABACO_DEPLOY_OPTS)

shell:
	bash $(SCRIPT_DIR)/run_container_process.sh bash

tests: tests-pytest tests-local

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

deploy: deploy-prod

deploy-prod: secrets-prod config-prod
	abaco deploy -F Dockerfile -B reactor.rc -t $(GITREF) $(ABACO_DEPLOY_OPTS) -U $(ACTOR_ID)

deploy-staging: secrets-staging config-staging
	abaco deploy -F Dockerfile.staging -k -B reactor-staging.rc -t $(GITREF) $(ABACO_DEPLOY_OPTS) -U $(ACTOR_ID)

postdeploy:
	bash tests/run_after_deploy.sh

samples:
	cp ../etl-pipeline-support/output/ginkgo/Novelchassis_Nand_gate_samples.json tests/data/samples-ginkgo.json
	cp ../etl-pipeline-support/output/biofab/provenance_dump.json tests/data/samples-biofab.json
	cp ../etl-pipeline-support/output/transcriptic/samples.json tests/data/samples-transcriptic.json
