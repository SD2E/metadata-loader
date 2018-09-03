from .basestore import *

class FileFixtyUpdateFailure(CatalogUpdateFailure):
    pass

class FileFixityStore(BaseStore):
    """Create and manage fixity records
    Records are linked with FilesMetadataStore via same uuid for a given filename"""
    def __init__(self, mongodb, config):
        super(FileFixityStore, self).__init__(mongodb, config)
        coll = config['collections']['fixity']
        if config['debug']:
            coll = '_'.join([coll, str(time_stamp(rounded=True))])
        self.name = coll
        self.coll = self.db[coll]

    def checkfile(self, filepath):
        '''Check if a filepath exists and is believed by the OS to be a file'''
        full_path = self.abspath(filepath)
        if os.path.isfile(full_path) and os.path.exists(full_path):
            return True
        else:
            return False

    def get_fixity_template(self, filename):
        t = {'original_filename': filename,
             'file_created': None,
             'file_modified': None,
             'created_date': None,
             'modified_date': None,
             'file_type': None,
             'size': None,
             'checksum': None,
             'lab': labname_from_path(filename)}
        return t

    def get_fixity_properties(self, filename, timestamp=None, properties={}):
        """Safely try to learn properties of filename
        Params:
            filename (str): a datafile.filename, which is a relative path
        Returns:
            dict containing a datafiles.properties
        """
        absfilename = self.abspath(filename)
        updated = False
        orig_properties = copy.deepcopy(properties)
        #properties = {}

        try:
            mtime = get_modification_date(absfilename)
            if mtime >= orig_properties.get('file_modified', mtime):
                updated = True
                properties['file_modified'] = mtime
                # be sure there's a file_created field and its not empty
                if properties.get('file_created', None) is None:
                    properties['file_created'] = mtime
        except Exception:
            pass
        # file type
        try:
            ftype = get_filetype(absfilename)
            properties['file_type'] = ftype
            if ftype != orig_properties.get('file_type', ftype):
                updated = True
        except Exception:
            pass
        # checksum
        try:
            cksum = compute_checksum(absfilename)
            properties['checksum'] = cksum
            if cksum != orig_properties.get('checksum', cksum):
                updated = True
        except Exception:
            pass
        # size in bytes
        try:
            size = get_size_in_bytes(absfilename)
            properties['size'] = size
            if size != orig_properties.get('size', size):
                updated = True
        except Exception:
            pass

        return properties

    def create_update_file(self, filename):
        """Create a DataFile record from a filename resolving to a physical path
        Parameters:
            filename (str) is the filename relative to DataCatalog.root
        Returns:
            dict-like PyMongo record
        """
        # To keep the update logic simple, this is independent of the code
        # for handling records from samples.json
        filename = self.normalize(filename)
        file_uuid = catalog_uuid(filename)
        ts = current_time()
        is_new_record = False

        # Exists?
        filerec = self.coll.find_one({'uuid': file_uuid})
        # ensure properties will have all the fields we want it to
        fixity_props = self.get_fixity_template(filename)
        if filerec is None:
            # new fixity record
            is_new_record = True
            # update properties with size, checksum, etc
            fixity_props = self.get_fixity_properties(filename,
                                                      properties=fixity_props)
            filerec = {'filename': filename,
                       'uuid': file_uuid,
                       'properties': fixity_props}

            # Create a revision field
            fixity_props['revision'] = 0
            # Record timestamps
            fixity_props['created_date'] = ts
            fixity_props['modified_date'] = ts
        else:
            # grab the properties from the existing record
            # print('record exists')
            orig_fixity_props = filerec.get('properties', {})
            # print('orig', orig_fixity_props)
            # clone them and try to update the copy
            fixity_props = self.get_fixity_properties(filename,
                                                      properties=copy.deepcopy(orig_fixity_props))
            # print('fixity', fixity_props)
            updated = False
            for cmp in ['checksum', 'size', 'lab', 'file_created', 'file_updated', 'file_type']:
                if cmp in orig_fixity_props and cmp in fixity_props:
                    if orig_fixity_props[cmp] != fixity_props[cmp]:
                        updated = True
                        # print('UPDATED {}'.format(cmp))

            if updated:
                # files are different
                # bump revision
                fixity_props['revision'] = fixity_props.get('revision', 0) + 1
                # bump updated
                fixity_props['modified_date'] = ts

            # merge new values onto original
            fixity_props = data_merge(orig_fixity_props, fixity_props)
            filerec['properties'] = fixity_props
            print(filerec['properties'])

            # Filter legacy properties
            # FIXME Take this code out once all files have been re-indexed
            for p in ['originator_id', 'inferred_file_type', 'declared_file_type', 'state', 'size_in_bytes']:
                try:
                    filerec['properties'].pop(p)
                except Exception:
                    pass
            # Filter legacy top-level keys
            # FIXME Take this code out once all files have been re-indexed
            for p in ['attributes', 'variables', 'annotations']:
                try:
                    filerec.pop(p)
                except Exception:
                    pass

        # Do the write
        try:
            if is_new_record:
                result = self.coll.insert_one(filerec)
                return self.coll.find_one({'_id': result.inserted_id})
            else:
                updated = self.coll.find_one_and_replace(
                    {'uuid': filerec['uuid']}, filerec,
                    return_document=ReturnDocument.AFTER)
                return updated
        except Exception as exc:
            raise FileUpdateFailure('write to data catalog failed', exc)

