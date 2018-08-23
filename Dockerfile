FROM sd2e/reactors:python3

ADD samples-schema.json /schemas/samples-schema.json

ADD datacatalog /datacatalog
ADD tests/data/samples.json /downloaded.json
# reactor.py, config.yml, and message.jsonschema will be automatically
# added to the container when you run docker build or abaco deploy
