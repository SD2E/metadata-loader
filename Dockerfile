FROM sd2e/reactors:python3-edge

COPY utils.py /utils.py

# ADD formats/targetschemas/samples-schema.json /schemas/samples-schema.json

# ADD datacatalog /datacatalog
# reactor.py, config.yml, and message.jsonschema will be automatically
# added to the container when you run docker build or abaco deploy
ADD tests/data /data
