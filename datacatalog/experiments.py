from .basestore import *

class ExperimentUpdateFailure(CatalogUpdateFailure):
    pass

class ExperimentStore(BaseStore):
    """Create and manage expts metadata
    Records are linked with samples via sample-specific uuid"""

    def __init__(self, mongodb, config):
        super(ExperimentStore, self).__init__(mongodb, config)
        coll = config['collections']['experiments']
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

    def create_update_experiment(self, expt, uuid=None):
        ts = current_time()
        expt_uuid = None
        # Absolutely must
        if 'experiment_reference' not in expt:
            raise ExperimentUpdateFailure(
                '"experiment_reference" is missing from experiment record')
        # Add UUID if it does not exist (record is likely new)
        if 'uuid' not in expt:
            expt_uuid = catalog_uuid(expt['experiment_reference'])
            expt['uuid'] = expt_uuid

        # Filter keys we manage elsewhere or that are otherwise uninformative
        for k in ['samples', 'challenge_problem']:
            try:
                expt.pop(k)
            except KeyError:
                pass

        # Try to fetch the existing record
        dbrec = self.coll.find_one({'uuid': expt_uuid})
        if dbrec is None:
            dbrec = expt
            expt['properties'] = {'created_date': ts,
                                    'modified_date': ts,
                                    'revision': 0}
            if 'samples_ids' not in expt:
                expt['samples_ids'] = []
            try:
                result = self.coll.insert_one(expt)
                return self.coll.find_one({'_id': result.inserted_id})
            except Exception as exc:
                raise ExperimentUpdateFailure('Failed to create experiment record', exc)
        else:
        # Update the fields content of the record using a rightward merge,
        # then update the updated and revision properties, then write the
        # record (and eventually its diff) to the catalog
            dbrec = self.update_properties(dbrec)
            dbrec_core = copy.deepcopy(dbrec)
            dbrec_props = dbrec_core.pop('properties')
            dbrec_meas_ids = []
            if 'samples_ids' in dbrec_core:
                dbrec_meas_ids = dbrec_core.pop('samples_ids')
            expt_core = copy.deepcopy(expt)
            # merge in fields data
            dbrec_core_1 = copy.deepcopy(dbrec_core)
            dbrec_core_1.pop('_id')
            new_rec, jdiff = data_merge_diff(dbrec_core, expt_core)
            # Store diff in our append-only updates log
            self.log(expt_uuid, jdiff)
#            print(json.dumps(jdiff, indent=2))
            new_rec['properties'] = dbrec_props
            new_rec['samples_ids'] = dbrec_meas_ids
            try:
                uprec = self.coll.find_one_and_replace(
                    {'_id': new_rec['_id']}, new_rec,
                    return_document=ReturnDocument.AFTER)
                return uprec
            except Exception as exc:
                raise ExperimentUpdateFailure(
                    'Failed to update existing expt', exc)

    def associate_ids(self, expt_uuid, ids):
        identifiers = copy.copy(ids)
        if not isinstance(identifiers, list):
            identifiers = [identifiers]
        meas = {'uuid': expt_uuid,
                'samples_ids': list(set(identifiers))}
        return self.create_update_experimentt(meas, uuid=expt_uuid)

    def delete_record(self, expt_id):
        '''Delete record by expt.id'''
        try:
            return self.coll.remove({'id': expt_id})
        except Exception as exc:
            raise ExperimentUpdateFailure(
                'Failed to delete expt {}'.format(expt_id), exc)

