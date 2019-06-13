import os
import json
import warnings
import copy
import jsonschema

from attrdict import AttrDict
import bacanora
import datacatalog

from reactors.runtime import Reactor, agaveutils

SCHEMA_FILE = '/schemas/samples-schema.json'
LOCALFILENAME = 'downloaded.json'
SCHEMA_URI = 'https://schema.catalog.sd2e.org/schemas/sample_set.json'

class formatChecker(jsonschema.FormatChecker):
    def __init__(self):
        jsonschema.FormatChecker.__init__(self)

def main():

    def on_failure(message, exception):
        if r.settings.pipelines.active:
            job.fail(message)
        r.on_failure(message, exception)

    def on_success(message):
        if r.settings.pipelines.active:
            job.finish(message)
        r.on_success(message)

    r = Reactor()
    m = AttrDict(r.context.message_dict)
    # ! This code fixes an edge case and will be moved lower in the stack
    if m == {}:
        try:
            jsonmsg = json.loads(r.context.raw_message)
            m = jsonmsg
        except Exception:
            pass

    # Use JSONschema-based message validator
    if not r.validate_message(m):
        r.on_failure('Invalid message received', ValueError())

    # Process options. Eventually move this into a Reactor method.
    # May need to add a filter to prevent some things from being over-written
    options_settings = {}
    if '__options' in m:
        # allow override of settings
        try:
            options_settings = m.get('options', {}).get('settings', {})
            if isinstance(options_settings, dict):
                options_settings = AttrDict(options_settings)
            r.settings = r.settings + options_settings
        except Exception as exc:
            on_failure('Failed to handle options', exc)

    agave_uri = m.get('uri')
    agave_sys, agave_path, agave_file = agaveutils.from_agave_uri(agave_uri)
    agave_full_path = os.path.join(agave_path, agave_file)

    if r.settings.pipelines.active:
        job = datacatalog.managers.pipelinejobs.ManagedPipelineJob(
            r.settings.mongodb,
            r.settings.pipelines,
            instanced=False,
            archive_path=agave_path
        )
        job.setup().run({'Processing': agave_uri})

    r.logger.debug('Downloading file')
    LOCALFILENAME = r.settings.downloaded
    try:
        bacanora.download(r.client, agave_full_path, LOCALFILENAME, agave_sys)
    except Exception as exc:
        # job.fail('Download failed')
        on_failure('Failed to download {}'.format(agave_file), exc)

    # Validate the downloaded file
    # (optional, controlled by config.yml#validate)
    if r.settings.validate:
        try:
            resolver = jsonschema.RefResolver('', '').resolve_remote(SCHEMA_URI)
            instance = json.load(open(LOCALFILENAME, 'r'))
            assert jsonschema.validate(instance, resolver,
                                       format_checker=formatChecker()) is None
        except Exception as exc:
            on_failure('Failed to validate downloaded file', exc)

    # TODO - Add optional validation of file references before loading data

    try:
        r.logger.debug(
            'Initializing SampleSetProcessor with {}'.format(r.client))
        db = datacatalog.managers.sampleset.SampleSetProcessor(
            r.settings.mongodb,
            agave=r.client,
            samples_file=agave_uri,
            samples_uri=LOCALFILENAME,
            path_prefix=agave_path)
        r.logger.debug('Now calling SampleSetProcessor.setup()')
        db.setup()
        r.logger.debug('Now calling SampleSetProcessor.process()')
        dbp = db.process()
        assert dbp is True
    except Exception as exc:
        on_failure('Ingest failed for {}'.format(agave_file), exc)

    if not r.local:
        r.loggers.slack.info(
            ':mario_star: Ingested {} ({} usec)'.format(agave_uri, r.elapsed()))

    on_success('Ingest complete for {} ({} usec)'.format(agave_uri, r.elapsed()))

if __name__ == '__main__':
    main()
