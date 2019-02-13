FROM sd2e/reactors:python3-edge

COPY bacanora /bacanora
# COPY utils.py /utils.py
# COPY formats/targetschemas/samples-schema.json /schemas/samples-schema.json
# COPY clients /pipelinesclient

# reactor.py, config.yml, and message.jsonschema will be automatically
# added to the container when you run docker build or abaco deploy
# ADD tests/data /data

# ADD datacatalog /datacatalog

# Comment out if not actively developing python-datacatalog
RUN pip uninstall --yes datacatalog || true

# Copy from local
# COPY datacatalog /datacatalog

# Install from Repo
RUN pip3 install --upgrade git+https://github.com/SD2E/python-datacatalog.git@0_2_0
