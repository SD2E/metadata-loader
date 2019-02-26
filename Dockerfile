FROM sd2e/reactors:python3-edge

COPY bacanora /bacanora
COPY utils.py /utils.py
# COPY formats/targetschemas/samples-schema.json /schemas/samples-schema.json
# COPY clients /pipelinesclient
# Comment out if not actively developing python-datacatalog
RUN pip uninstall --yes datacatalog || true

# Install from Repo
RUN pip3 install --upgrade git+https://github.com/SD2E/python-datacatalog.git@v1.0.0
