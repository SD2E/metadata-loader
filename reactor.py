import os
import json
import warnings
import copy
from attrdict import AttrDict
from reactors.runtime import Reactor, agaveutils

from jsonschema import validate, RefResolver
from datacatalog import CatalogStore, SampleStore, MeasurementStore
from datacatalog import posixhelpers, data_merge
from datacatalog.agavehelpers import from_agave_uri

SCHEMA_FILE = '/schemas/samples-schema.json'
LOCALFILENAME = '/downloaded.json'

def validate_file_schema(filename, schema_file=SCHEMA_FILE, permissive=False):
    '''
    Validate a JSON document against a JSON schema

    Positional arguments:
    filename - str - path to the JSON file to validate

    Keyword arguments:
    schema_file - str - path to the requisite JSON schema file
    permissive - bool - swallow validation errors [False]
    '''
    try:
        with open(filename) as object_file:
            object_json = json.loads(object_file.read())

        with open(schema_file) as schema:
            schema_json = json.loads(schema.read())
            schema_abs = 'file://' + schema_file
    except Exception as e:
        raise Exception("file or schema loading error", e)

    class fixResolver(RefResolver):
        def __init__(self):
            RefResolver.__init__(self, base_uri=schema_abs, referrer=None)
            self.store[schema_abs] = schema_json

    try:
        validate(object_json, schema_json, resolver=fixResolver())
        return True
    except Exception as e:
        if permissive is False:
            raise Exception("file validation failed", e)
        else:
            pass

def compute_prefix(uri, catalog_root='/', prefix=None):
    new_prefix = ''
    if prefix is not None:
        return prefix
    else:
        agave_sys, agave_path, agave_file = from_agave_uri(uri)
        new_prefix = agave_path.replace(catalog_root, '')
        if new_prefix.startswith('/'):
            new_prefix = new_prefix[1:]
    return new_prefix

def main():
    # { "uri": "agave://storagesystem/uploads/path/to/target.txt"}

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

    # Set up Store objects
    files_store = CatalogStore(mongodb=r.settings.mongodb,
                                  config=r.settings.catalogstore)

    sample_store = SampleStore(mongodb=r.settings.mongodb,
                               config=r.settings.catalogstore)

    meas_store = MeasurementStore(mongodb=r.settings.mongodb,
                                  config=r.settings.catalogstore)

    r.logger.debug('collections: {}, {}, {}'.format(files_store.name,
                   sample_store.name, meas_store.name))

    agave_uri = m.get('uri')
    agave_sys, agave_path, agave_file = from_agave_uri(agave_uri)
    agave_full_path = os.path.join(agave_path, agave_file)
    # to_process = m.get('reprocess', [])
    filename_prefix = compute_prefix(
        agave_uri, r.settings.catalogstore.store, m.get('prefix', None))

    r.logger.debug('computed filename prefix: {}'.format(filename_prefix))

    r.logger.debug('downloading file')
    if r.local is False:
        try:
            agaveutils.agave_download_file(
                agaveClient=r.client,
                agaveAbsolutePath=agave_full_path,
                systemId=agave_sys,
                localFilename=LOCALFILENAME)
        except Exception as exc:
            r.on_failure('download failed', exc)

    r.logger.debug('validating file against schema')
    try:
        validate_file_schema(LOCALFILENAME)
    except Exception as exc:
        r.on_failure('validation failed', exc)

    r.logger.debug('extending file names with root path')
    with open(LOCALFILENAME, 'r') as samplesfile:
        filedata = json.load(samplesfile)
        if 'samples' in filedata:
            for sample in filedata['samples']:
                # Change keyname to id since we're already in the samples collection
                sample['id'] = sample['sample_id']
                sample.pop('sample_id')

        # set to -1 for no limit
        max_samples = 1
        # Write samples, measurement, files record(s)
        samp_meas_assoc = {}
        meas_file_assoc = {}
        samples_set = filedata.pop('samples')
        for s in samples_set:
            r.logger.info('PROCESSING SAMPLE {}'.format(s['id']))
            samp_extras = {'filename': sample_store.normalize(agave_full_path)}
            samp_rec = data_merge(copy.deepcopy(s), samp_extras)
            r.logger.debug(
                'writing sample record {}'.format(samp_rec['id']))
            sid = None
            try:
                new_samp = sample_store.create_update_sample(samp_rec)
                sid = new_samp['uuid']
                if sid not in samp_meas_assoc:
                    samp_meas_assoc[sid] = []
            except Exception as exc:
                r.on_failure('sample write failed', exc)

            try:
                meas = s.pop('measurements')
                for m in meas:
                    r.logger.info('PROCESSING MEASUREMENT {}'.format(m['measurement_id']))
                    meas_extras = {}
                    meas_rec = data_merge(copy.deepcopy(m), meas_extras)
                    mid = None
                    try:
                        new_meas = meas_store.create_update_measurement(meas_rec)
                        mid = new_meas['uuid']
                        if new_meas['uuid'] not in samp_meas_assoc[sid]:
                            r.logger.debug('extending sample.measurement_ids')
                            samp_meas_assoc[sid].append(new_meas['uuid'])
                    except Exception as exc:
                        r.on_failure('measurement write failed', exc)

                    # Iterate through file records
                    try:
                        files = meas_rec.get('files', [])
                        r.logger.debug('file count: {}'.format(len(files)))
                        for f in files:
                            r.logger.info(
                                'PROCESSING FILE {}'.format(f['name']))
                            # Transform into a CatalogStore record
                            # FIXME Make resilient to missing keys
                            file_copy = copy.deepcopy(f)
                            file_orig_name = file_copy.pop('name')
                            file_type = file_copy.pop('type')
                            file_state = file_copy.pop('state')
                            file_name = files_store.normalize(os.path.join(
                                agave_path, file_orig_name))
                            # TODO Improve file_type once we've improve filetype mapping
                            file_record = {'filename': file_name, 'state': file_state,
                                            'properties': {'declared_file_type': file_type,
                                                            'original_filename': file_orig_name}}

                            try:
                                r.logger.debug(
                                'writing file record for {}'.format(f['name']))
                                file_rec_resp = files_store.create_update_record(file_record)
                                if 'uuid' in file_rec_resp:
                                    if not mid in meas_file_assoc:
                                        meas_file_assoc[mid] = []
                                    if file_rec_resp['uuid'] not in meas_file_assoc[mid]:
                                        r.logger.debug(
                                            'extending measurement.files_uuids')
                                        meas_file_assoc[mid].append(file_rec_resp['uuid'])
                                else:
                                    r.logger.critical(
                                        'file uuid-to-measurement association failed')
                            except Exception as exc:
                                r.logger.critical('files write failed')
                    except KeyError as kexc:
                        r.logger.warning('unable to process files: {}'.format(kexc))
            except Exception as exc:
                r.logger.critical('unable to process measurements for sample')

            max_samples = max_samples - 1
            if max_samples == 0:
                break

        try:
            for si in samp_meas_assoc:
                sample_store.associate_ids(si, samp_meas_assoc[si])
        except Exception as exc:
            r.logger.critical(
                'failed to associate measurements with samples: {}'.format(exc))

        try:
            for mi in meas_file_assoc:
                meas_store.associate_ids(mi, meas_file_assoc[mi])
        except Exception as exc:
            r.logger.critical('failed to associate files with measurements: {}'.format(exc))

if __name__ == '__main__':
    main()
