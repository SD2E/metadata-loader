import os
import json
import re
import warnings
import copy
from attrdict import AttrDict
from reactors.runtime import Reactor, agaveutils
from jsonschema import validate, RefResolver
from datacatalog import CatalogStore, SampleStore, MeasurementStore
from datacatalog import posixhelpers, dict_merge

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

def from_agave_uri(uri=None, Validate=False):
    '''
    Parse an Agave URI into a tuple (systemId, directoryPath, fileName)
    Validation that it points to a real resource is not implemented. The
    same caveats about validation apply here as in to_agave_uri()
    '''
    systemId = None
    dirPath = None
    fileName = None
    proto = re.compile(r'agave:\/\/(.*)$')
    if uri is None:
        raise Exception("URI cannot be empty")
    resourcepath = proto.search(uri)
    if resourcepath is None:
        raise Exception("Unable resolve URI")
    resourcepath = resourcepath.group(1)
    firstSlash = resourcepath.find('/')
    if firstSlash is -1:
        raise Exception("Unable to resolve systemId")
    try:
        systemId = resourcepath[0:firstSlash]
        origDirPath = resourcepath[firstSlash + 1:]
        dirPath = '/' + os.path.dirname(origDirPath)
        fileName = os.path.basename(origDirPath)
        return (systemId, dirPath, fileName)
    except Exception as e:
        raise Exception("Error resolving directory path or file name: {}".format(e))


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

    r.logger.debug(files_store.coll)
    r.logger.debug(sample_store.coll)
    r.logger.debug(meas_store.coll)

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
        r.on_failure('schema validation failed', exc)

    r.logger.info('extending file names with catalog-relative path')
    samples_with_measurements = 0
    with open(LOCALFILENAME, 'r') as samplesfile:
        filedata = json.load(samplesfile)
        if 'samples' in filedata:
            for sample in filedata['samples']:
                # Change keyname to id since we're already in the samples collection
                sample['id'] = sample['sample_id']
                sample.pop('sample_id')
        #         if 'measurements' in sample:
        #             samples_with_measurements += 1
        #             for meas in sample['measurements']:
        #                 files_copy = copy.deepcopy(meas['files'])
        #                 files_resolved = []
        #                 for file in files_copy:
        #                     try:
        #                         # Raises ValueError if path can't rebase
        #                         new_filename = posixhelpers.rebase_file_path(
        #                             file['name'], filename_prefix)
        #                         file['name'] = new_filename
        #                         files_resolved.append(file)
        #                     except ValueError as exc:
        #                         pass
        #                         #r.logger.warn(exc)
        #                 meas['files'] = files_resolved
        #         else:
        #             pass
                    #r.logger.warning('no measurements found for sample {}'.format(sample['id']))

        # Deal with "chatty" trace dumps that can't be associated with
        # files in the present working directory
        #
        # 1. Filter measurements where there are no files
        # for sample in filedata['samples']:
        #     meas_copy = copy.deepcopy(sample['measurements'])
        #     meas_kept = []
        #     for meas in meas_copy:
        #         if len(meas['files']) > 0:
        #             meas_kept.append(meas)
        #     sample['measurements'] = meas_kept
        # # 2. Filter samples where there are no measurements
        # samples_copy = copy.deepcopy(filedata['samples'])
        # samples_kept = []
        # for sample in samples_copy:
        #     if len(sample['measurements']) > 0:
        #         samples_kept.append(sample)
        # filedata['samples'] = samples_kept

        # Write samples, measurement, files record(s)
        samples_set = filedata.pop('samples')
        for s in samples_set:
            r.logger.info('PROCESSING SAMPLE {}'.format(s['id']))
            try:
                meas = s.pop('measurements')
                s['measurement_ids'] = []
                for m in meas:
                    r.logger.info('PROCESSING MEASUREMENT {}'.format(m['measurement_id']))
                    if isinstance(m, dict):
                        try:
                            # FILES
                            files = m.pop('files')
                            r.logger.debug('file count: {}'.format(len(files)))
                            m['files_id'] = []
                            for f in files:
                                r.logger.info(
                                    'PROCESSING FILE {}'.format(f['name']))
                                # Transform into a CatalogStore record
                                file_copy = copy.deepcopy(f)
                                file_orig_name = file_copy.pop('name')
                                file_type = file_copy.pop('type')
                                file_state = file_copy.pop('state')
                                file_name = files_store.normalize(os.path.join(
                                    agave_path, file_orig_name))
                                # TODO Improve file_type when we improve filetype mapping
                                file_record = {'filename': file_name, 'state': file_state,
                                               'properties': {'declared_file_type': file_type,
                                                              'original_filename': file_orig_name}}
                                r.logger.debug(
                                    'creating or updating file {}'.format(f['name']))
                                file_rec_resp = files_store.create_update_record(file_record)
                                #print(file_rec_resp)
                                if 'uuid' in file_rec_resp:
                                    r.logger.info('associating file {} with measurement'.format(
                                        file_rec_resp['uuid']))
                                    if file_rec_resp['uuid'] not in m['files_id']:
                                        m['files_id'].append(file_rec_resp['uuid'])
                                else:
                                    raise KeyError('files record cannot be associated with measurement')
                        except KeyError as kerr:
                            r.logger.warning('measurement had no files slot', kerr)
                    meas_extras = {}
                    meas_rec = dict_merge(copy.deepcopy(m), meas_extras)
                    #r.logger.info('creating or updating a measurement record for sample {}'.format(s['id']))
                    try:
                        new_meas = meas_store.create_update_measurement(meas_rec)
                        s['measurement_ids'].append(new_meas['uuid'])
                    except Exception as exc:
                        r.on_failure('failed to write measurement record', exc)
            except KeyError:
                pass
            srec = dict_merge(copy.deepcopy(filedata), s)
            # add source URI
            srec['filename'] = sample_store.normalize(agave_full_path)
            #r.logger.info('creating or updating sample record for sample {}'.format(srec['id']))
            try:
                sample_store.create_update_sample(srec)
            except Exception as exc:
                r.on_failure('failed to write sample record', exc)


        r.logger.info('{} samples found with measurements'.format(samples_with_measurements))

        # Write out measurement sets


    # r.logger.debug('output sample records')
    # with open('samples-transformed.json', 'w+') as st:
    #     json.dump(filedata, st, indent=4)


    # store = CatalogStore(mongodb=r.settings.mongodb,
    #                      config=r.settings.catalogstore)
    # try:
    #     resp = sample_store.create_update_record(agave_full_path)
    #     r.logger.info('DataFile._id {} created or updated'.format(
    #         resp.get('uuid', None)))
    # except Exception as exc:
    #     r.on_failure('Failed to process file {}'.format(agave_full_path), exc)

if __name__ == '__main__':
    main()
