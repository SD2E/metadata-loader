from .basestore import *

class SampleUpdateFailure(CatalogUpdateFailure):
    pass
class SampleStore(BaseStore):
    """Create and manage samples metadata
    Records are linked with Measurements via measurement-specific uuid"""

    def __init__(self, mongodb, config):
        super(SampleStore, self).__init__(mongodb, config)
        coll = config['collections']['samples']
        if config['debug']:
            coll = '_'.join([coll, str(time_stamp(rounded=True))])
        self.name = coll
        self.coll = self.db[coll]

    def update_properties(self, dbrec):
        ts = current_time()
        properties = dbrec.get('properties', {})
        properties['created_date'] = properties.get('created_date', ts)
        if properties.get('modified_date', ts) >= ts:
            properties['modified_date'] = ts
        properties['revision'] = properties.get('revision', 0) + 1
        dbrec['properties'] = data_merge(dbrec['properties'], properties)
        return dbrec

    def create_update_sample(self, sample, suuid=None):
        ts = current_time()
        samp_uuid = None
        # Absolutely must
        if 'id' not in sample:
            raise SampleUpdateFailure('"id" missing from sample')
        # Add UUID if it does not exist (record is likely new)
        if 'uuid' not in sample:
            samp_uuid = catalog_uuid(sample['id'])
            sample['uuid'] = samp_uuid

        # Filter keys we manage elsewhere
        try:
            sample.pop('measurements')
        except KeyError:
            pass

        # Try to fetch the existing record
        dbrec = self.coll.find_one({'uuid': samp_uuid})
        if dbrec is None:
            dbrec = sample
            sample['properties'] = {'created_date': ts,
                                    'modified_date': ts,
                                    'revision': 0}
            if 'measurements_ids' not in sample:
                sample['measurements_ids'] = []
            try:
                result = self.coll.insert_one(sample)
                return self.coll.find_one({'_id': result.inserted_id})
            except Exception as exc:
                raise SampleUpdateFailure('Failed to create sample', exc)
        else:
        # Update the fields content of the record using a rightward merge,
        # then update the updated and revision properties, then write the
        # record (and eventually its diff) to the catalog
            dbrec = self.update_properties(dbrec)
            dbrec_core = copy.deepcopy(dbrec)
            dbrec_props = dbrec_core.pop('properties')
            dbrec_meas_ids = []
            if 'measurements_ids' in dbrec_core:
                dbrec_meas_ids = dbrec_core.pop('measurements_ids')
            sample_core = copy.deepcopy(sample)
            # merge in fields data
            dbrec_core_1 = copy.deepcopy(dbrec_core)
            dbrec_core_1.pop('_id')
            new_rec, jdiff = data_merge_diff(dbrec_core, sample_core)
            # Store diff in our append-only updates log
            self.log(samp_uuid, jdiff)
#            print(json.dumps(jdiff, indent=2))
            new_rec['properties'] = dbrec_props
            new_rec['measurements_ids'] = dbrec_meas_ids
            try:
                uprec = self.coll.find_one_and_replace(
                    {'_id': new_rec['_id']}, new_rec,
                    return_document=ReturnDocument.AFTER)
                return uprec
            except Exception as exc:
                raise SampleUpdateFailure(
                    'Failed to update existing sample', exc)

    def associate_ids(self, samp_uuid, ids):
        identifiers = copy.copy(ids)
        if not isinstance(identifiers, list):
            identifiers = [identifiers]
        meas = {'uuid': samp_uuid,
                'measurements_ids': list(set(identifiers))}
        return self.create_update_sample(meas, suuid=samp_uuid)

    def delete_record(self, sample_id):
        '''Delete record by sample.id'''
        try:
            return self.coll.remove({'id': sample_id})
        except Exception:
            raise SampleUpdateFailure(
                'Failed to delete sample {}'.format(sample_id))

