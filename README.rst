Samples Metadata Loader
=======================

Accepts
-------

- The deployed actor responds to a JSON message in this schema, where the URI points to a lab metadata file

.. code-block:: json

    {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://schema.catalog.sd2e.org/schemas/agave-files-uri-message.json"
        "title": "AgaveFilesUriMessage",
        "description": "Request conversion of a lab samples file",
        "type": "object",
        "additionalProperties": false,
        "properties": {
            "uri": {
                "$ref": "agave_files_uri.json"
                "description": "Agave-canonical path to a lab metadata file"
            },
            "options" : {
                "type": "object",
                "description": "Optional kwargs-style options dictionary"
            }
        },
        "required": ["uri"]
    }

Returns
-------

The actor loads or updates the MongoDb that underpins the Data Catalog
system. It produces no file products, nor does it message other actors.

1. Slack messages to ``#notifications`` are generated at start and on success or failure
2. Logs are aggregrated in the project-wide `Logtrail <https://kibana.sd2e.org/app/logtrail#/>`_

Interactive Usage
-----------------

This project is not intended for interactive usage.

Developing
----------

