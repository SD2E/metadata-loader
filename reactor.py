import os
import json
import warnings
import copy

from attrdict import AttrDict
import bacanora
import datacatalog

from reactors.runtime import Reactor, agaveutils

SCHEMA_FILE = '/schemas/samples-schema.json'
LOCALFILENAME = 'downloaded.json'

def main():

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
        r.on_failure('Invalid message received', None)

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
            r.on_failure('Failed to handle options', exc)

        print(r.settings)

    agave_uri = m.get('uri')
    agave_sys, agave_path, agave_file = agaveutils.from_agave_uri(agave_uri)
    agave_full_path = os.path.join(agave_path, agave_file)

    # job = ReactorsPipelineJobClient(r, m)
    # job.setup().run({'Processing': agave_uri})

    r.logger.debug('Downloading file')
    LOCALFILENAME = r.settings.downloaded
    try:
        bacanora.download(r.client, agave_full_path, LOCALFILENAME, agave_sys)
    except Exception as exc:
        # job.fail('Download failed')
        r.on_failure('download failed', exc)

    db = datacatalog.managers.sampleset.SampleSetProcessor(r.settings.mongodb,
                                                           samples_file=LOCALFILENAME,
                                                           path_prefix=agave_path)
    try:
        dbp = db.process()
        assert dbp is True
    except Exception as exc:
        r.on_failure('Metadata ingest failed', exc)

    # job.finish('Ingest completed')

    r.loggers.slack.info(
        ':mario_star: Ingested {} ({} usec)'.format(agave_uri, r.elapsed()))
    r.logger.info('INGESTED {} ({} usec)'.format(agave_uri, r.elapsed()))

if __name__ == '__main__':
    main()
