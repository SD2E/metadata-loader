from .basestore import *

class FileMetadataUpdateFailure(CatalogUpdateFailure):
    pass

class FileMetadataStore(BaseStore):
    """Create and manage files metadata records.
    Records are linked with FixityStore via shared uuid for a each filename and
    to files via that UUID"""
    def __init__(self, mongodb, config):
        super(FileMetadataStore, self).__init__(mongodb, config)
        coll = config['collections']['files']
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

    def create_update_file(self, file, parents=None, uuid=None):
        """Create or update a file metadata record using its data catalog store-
        relative path as a primary key"""
        ts = current_time()
        file_uuid = None

        # Absolutely must
        if 'name' not in file:
            raise FileMetadataUpdateFailure(
                '"name" missing from file record')

        # transformations
        # replace name w filename
        filename = self.normalize(file['name'])
        file.pop('name')
        file['filename'] = filename
        # Add UUID if it does not exist (record is likely new)
        if 'uuid' not in file:
            file_uuid = catalog_uuid(filename)
            file['uuid'] = file_uuid
        # move keys that overlap with fixity data model into properties
        # if 'properties' not in file:
        #     file['properties'] = {}
        if 'type' in file:
            file['file_type'] = file.pop('type')
        if 'state' in file:
            file['level'] = file.pop('state')

        # this list maintains the inheritance relationship
        # in this case, a list of measurement uuids
        # allow overloading parents as string or array or None
        if parents is None:
            parents = []
        if isinstance(parents, str):
            parents = [parents]
        file['child_of'] = parents

        # # Filter keys we manage elsewhere or that are otherwise uninformative
        # for k in ['files', 'files_ids']:
        #     try:
        #         file.pop(k)
        #     except KeyError:
        #         pass

        # Try to fetch the existing record
        dbrec = self.coll.find_one({'uuid': file_uuid})
        if dbrec is None:
            dbrec = file
            file['properties'] = {'created_date': ts,
                                  'modified_date': ts,
                                  'revision': 0}
            # if 'files_ids' not in file:
            #     file['files_ids'] = []
            try:
                result = self.coll.insert_one(file)
                return self.coll.find_one({'_id': result.inserted_id})
            except Exception:
                raise FileMetadataUpdateFailure(
                    'Failed to create file metadata')
        else:
            # Update the fields content of the record using a rightward merge,
            # then update the updated and revision properties, then write the
            # record (and eventually its diff) to the catalog
            dbrec = self.update_properties(dbrec)
            dbrec_core = copy.deepcopy(dbrec)
            dbrec_props = dbrec_core.pop('properties')
            # dbrec_files_ids = []
            # if 'files_ids' in dbrec_core:
            #     dbrec_files_ids = dbrec_core.pop('files_ids')
            file_core = copy.deepcopy(file)
            # merge in fields data
            dbrec_core_1 = copy.deepcopy(dbrec_core)
            dbrec_core_1.pop('_id')
            new_rec, jdiff = data_merge_diff(dbrec_core, file_core)
            # Store diff in our append-only updates log
            self.log(file_uuid, jdiff)
#            print(json.dumps(jdiff, indent=2))
            new_rec['properties'] = dbrec_props
#            new_rec['files_ids'] = dbrec_files_ids
            try:
                uprec = self.coll.find_one_and_replace(
                    {'_id': new_rec['_id']}, new_rec,
                    return_document=ReturnDocument.AFTER)
                return uprec
            except Exception as exc:
                raise FileMetadataUpdateFailure(
                    'Failed to update existing file', exc)

    def delete_record(self, filename):
        '''Delete record by filename'''
        try:
            file_uuid = catalog_uuid(filename)
            return self.coll.remove({'uuid': file_uuid})
        except Exception:
            raise FileMetadataUpdateFailure(
                'Failed to delete metadata for {}'.format(filename))

    def associate_ids(self, meas_uuid, ids):
        identifiers = copy.copy(ids)
        if not isinstance(identifiers, list):
            # using list on a str will return a character iterator
            identifiers = [identifiers]
        meas = {'uuid': meas_uuid,
                'files_ids': list(set(identifiers))}
        return self.create_update_file(meas, uuid=meas_uuid)
