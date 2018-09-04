from .basestore import *

class MeasurementUpdateFailure(CatalogUpdateFailure):
    pass
class MeasurementStore(BaseStore):
    """Create and manage measurements metadata
    Records are linked with Files via file-specific uuid"""

    def __init__(self, mongodb, config):
        super(MeasurementStore, self).__init__(mongodb, config)
        coll = config['collections']['measurements']
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

    def create_update_measurement(self, measurement, parents=None, uuid=None, attributes={}):
        ts = current_time()
        samp_uuid = None
        # Absolutely must
        if 'measurement_id' not in measurement:
            raise MeasurementUpdateFailure(
                '"measurement_id" missing from measurement')
        # Add UUID if it does not exist (record is likely new)
        if 'uuid' not in measurement:
            samp_uuid = catalog_uuid(measurement['measurement_id'])
            measurement['uuid'] = samp_uuid

        # accept attributes overrides
        if 'attributes' not in measurement:
            measurement['attributes'] = {}
        for k, v in attributes.items():
            measurement['attributes'][k] = v

        # this list maintains the inheritance relationship
        # in this case, a list of sample uuids
        if parents is None:
            parents = []
        if isinstance(parents, str):
            parents = [parents]
        measurement['child_of'] = parents
        # Filter keys we manage elsewhere or that are otherwise uninformative
        for k in ['files']:
            try:
                measurement.pop(k)
            except KeyError:
                pass

        # Try to fetch the existing record
        dbrec = self.coll.find_one({'uuid': samp_uuid})
        if dbrec is None:
            dbrec = measurement
            measurement['properties'] = {'created_date': ts,
                                         'modified_date': ts,
                                         'revision': 0}
            try:
                result = self.coll.insert_one(measurement)
                return self.coll.find_one({'_id': result.inserted_id})
            except Exception as exc:
                raise MeasurementUpdateFailure('Failed to create measurement', exc)
        else:
            # Update the fields content of the record using a rightward merge,
            # then update the updated and revision properties, then write the
            # record (and eventually its diff) to the catalog
            dbrec = self.update_properties(dbrec)
            dbrec_core = copy.deepcopy(dbrec)
            dbrec_props = dbrec_core.pop('properties')
            measurement_core = copy.deepcopy(measurement)
            # merge in fields data
            dbrec_core_1 = copy.deepcopy(dbrec_core)
            dbrec_core_1.pop('_id')
            new_rec, jdiff = data_merge_diff(dbrec_core, measurement_core)
            # Store diff in our append-only updates log
            self.log(samp_uuid, jdiff)
#            print(json.dumps(jdiff, indent=2))
            new_rec['properties'] = dbrec_props
            try:
                uprec = self.coll.find_one_and_replace(
                    {'_id': new_rec['_id']}, new_rec,
                    return_document=ReturnDocument.AFTER)
                return uprec
            except Exception as exc:
                raise MeasurementUpdateFailure(
                    'Failed to update existing measurement', exc)

    def delete_record(self, measurement_id):
        '''Delete record by measurement.id'''
        try:
            meas_uuid = catalog_uuid(measurement_id)
            return self.coll.remove({'uuid': measurement_id})
        except Exception as exc:
            raise MeasurementUpdateFailure(
                'Failed to delete measurement {}'.format(meas_uuid), exc)