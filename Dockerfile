FROM sd2e/reactors:python3-edge

# COPY bacanora /bacanora

# Comment out if not actively developing python-datacatalog
RUN pip uninstall --yes datacatalog || true

# Install from Repo
RUN pip3 install --upgrade git+https://github.com/SD2E/python-datacatalog.git@2_0

RUN pip3 install --upgrade git+https://github.com/SD2E/bacanora.git@master

ENV CATALOG_ADMIN_TOKEN_KEY=ErWcK75St2CUetMn7pzh8EwzAhn9sHHK54nA
ENV CATALOG_ADMIN_TOKEN_LIFETIME=3600
ENV CATALOG_RECORDS_SOURCE=metadata-loader
ENV CATALOG_STORAGE_SYSTEM=data-sd2e-community
