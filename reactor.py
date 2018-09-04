import os
import json
import warnings
import copy
from attrdict import AttrDict
from reactors.runtime import Reactor, agaveutils

from datacatalog import FileMetadataStore, SampleStore, MeasurementStore, ExperimentStore, ChallengeStore
from datacatalog import posixhelpers, data_merge, validate_file_to_schema
from datacatalog.agavehelpers import from_agave_uri

SCHEMA_FILE = '/schemas/samples-schema.json'
# LOCALFILENAME = 'downloaded.json'
LOCALFILENAME = '/data/samples-biofab.json'

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
    chall_store = ChallengeStore(mongodb=r.settings.mongodb,
                                 config=r.settings.catalogstore)

    expt_store = ExperimentStore(mongodb=r.settings.mongodb,
                                 config=r.settings.catalogstore)

    sample_store = SampleStore(mongodb=r.settings.mongodb,
                               config=r.settings.catalogstore)

    meas_store = MeasurementStore(mongodb=r.settings.mongodb,
                                  config=r.settings.catalogstore)

    files_store = FileMetadataStore(mongodb=r.settings.mongodb,
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

    r.logger.debug('validating file against samples schema')
    try:
        validate_file_to_schema(LOCALFILENAME, SCHEMA_FILE)
    except Exception as exc:
        r.on_failure('validation failed', exc)

    with open(LOCALFILENAME, 'r') as samplesfile:
        filedata = json.load(samplesfile)

        # set to -1 for no limit
        max_samples = -1
        # Write samples, measurement, files record(s)
        chall_expt_assoc = {}
        expt_samp_assoc = {}
        samp_meas_assoc = {}
        meas_file_assoc = {}
        samples_set = filedata.pop('samples')

        # create challenge problem record
        r.logger.info('PROCESSING CHALLENGE PROBLEM {}'.format(filedata['challenge_problem']))
        lab_name = filedata.get('lab', 'Unknown')
        cp_extras = {'filename': expt_store.normalize(agave_full_path)}
        cp_rec = data_merge(copy.deepcopy(filedata), cp_extras)
        r.logger.debug('writing challenge problem record {}'.format(cp_rec['challenge_problem']))
        cid = None
        try:
            new_samp = chall_store.create_update_challenge(cp_rec, parents=[])
            cid = new_samp['uuid']
            if cid not in expt_samp_assoc:
                expt_samp_assoc[cid] = []
        except Exception as exc:
            r.logger.critical('challenge problem write failed: {}'.format(exc))

        # create experiment record
        # NOTE: Currently failing to do the right thing because we don't have experiment_reference maps
        r.logger.info('PROCESSING EXPERIMENT {}'.format(
            filedata['experiment_reference']))
        expt_extras = {'filename': expt_store.normalize(agave_full_path)}
        expt_rec = data_merge(copy.deepcopy(filedata), expt_extras)
        r.logger.debug('writing experiment record {}'.format(expt_rec['experiment_reference']))
        eid = None
        try:
            new_samp = expt_store.create_update_experiment(expt_rec, parents=cid)
            eid = new_samp['uuid']
            if eid not in expt_samp_assoc:
                expt_samp_assoc[eid] = []
        except Exception as exc:
            r.logger.critical('expt write failed: {}'.format(exc))

        # process samples, measurements, files...
        for s in samples_set:
            r.logger.info('PROCESSING SAMPLE {}'.format(s['sample_id']))
            samp_extras = {'filename': sample_store.normalize(agave_full_path)}
            samp_rec = data_merge(copy.deepcopy(s), samp_extras)
            r.logger.debug(
                'writing sample record {}'.format(samp_rec['sample_id']))
            sid = None
            try:
                new_samp = sample_store.create_update_sample(
                    samp_rec, parents=eid, attributes={'lab': lab_name})
                sid = new_samp['uuid']
                if sid not in samp_meas_assoc:
                    samp_meas_assoc[sid] = []
            except Exception as exc:
                r.logger.critical('sample write failed: {}'.format(exc))

            if 'measurements' in s:
                try:
                    meas = s.get('measurements')
                    for m in meas:
                        r.logger.info('PROCESSING MEASUREMENT {}'.format(m.get('measurement_id', 'Undefined')))
                        meas_extras = {}
                        meas_rec = data_merge(copy.deepcopy(m), meas_extras)
                        mid = None
                        try:
                            new_meas = meas_store.create_update_measurement(
                                meas_rec, parents=sid)
                            mid = new_meas['uuid']
                            if new_meas['uuid'] not in samp_meas_assoc[sid]:
                                r.logger.debug('extending sample.measurement_ids')
                                samp_meas_assoc[sid].append(new_meas['uuid'])
                        except Exception as exc:
                            r.logger.critical('measurement write failed: {}'.format(exc))

                        # Iterate through file records
                        if 'files' in m:
                            files = m.get('files', [])
                            for f in files:
                                r.logger.info(
                                    'PROCESSING FILE {}'.format(f['name']))
                                try:
                                    r.logger.debug(
                                        'writing file record for {}'.format(f['name']))
                                    file_resp = files_store.create_update_file(f, path=agave_path, parents=mid)
                                    if 'uuid' in file_resp:
                                        r.logger.debug('wrote FileMetadata.uuid {}'.format(file_resp['uuid']))
                                except Exception as exc:
                                    r.logger.critical('file write failed: {}'.format(exc))

                except Exception as exc:
                    raise Exception(exc)

                max_samples = max_samples - 1
                if max_samples == 0:
                    break


if __name__ == '__main__':
    main()
