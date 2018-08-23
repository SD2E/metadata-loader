Ingest Samples JSON
===================

This actor captures the samples.json record for uploaded files in the SD2E Data
Catalog, which is currently a MongoDB database, via methods defined in
`datacatalog`. This is a prototype module containing common methods used by
Python applications to interact with the Data Catalog and will be factored out
into a standalone module in Q42018.

Schema
------

The schema currently being implemented for the Data Catalog can be found in
`DataFile.jsonschema` in the datacatalog module.

Workflow
--------

This actor's logic is as follows:

1. Accept a message containing an Agave-canonical URI for a samples.json file
2. Retrieve the file
3. Determine the prefix for files represented in samples.json
    1. If `prefix` is passed in the message:
        1. Use it.
    2. Else:
        1. Use relative path of samples.json parent to Data Catalog root
4. Validate it against the samples.json schema
5. For each file record in samples.json, use `prefix` to build `filename`
    1. If `filename` resolves to a real file
        1. Amend the file record in memory
    2. Else:
        1. Raise a warning
        2. Collect the names that fail to resolve into `reprocess`

Decide whether to write the record: Default is to write. We only want to skip on futile cycles where the reprocess queue hasn't changed.

1. Was there a `reprocess` slot in the message?
    1. No:
        1. Update the record
    2. Yes:
        1. Is the computed version of `reprocess` different than the one in the message?
            1. Yes:
                1. Update the record
            2. No
                1. Skip update

