import arrow
import datetime
import pytz
import json
import uuid
import copy
import collections
from slugify import slugify
from pymongo import MongoClient, ReturnDocument
from bson.binary import Binary, UUID_SUBTYPE
try:
    # Python 3.x
    from urllib.parse import quote_plus
except ImportError:
    # Python 2.x
    from urllib import quote_plus
from .constants import *
from .posixhelpers import *
from .constants import *

# FIXME The *Store classes are not DRY at all. Bring a towel.
# FIXME Code relies too much on hard-coded reference integrity

class CatalogError(Exception):
    pass

class CatalogUpdateFailure(CatalogError):
    # Errors arising when the Data Catalog can't be updated
    pass

class CatalogDataError(CatalogError):
    # Errors arising from computing or validating metadata
    pass

class CatalogDatabaseError(CatalogError):
    # Errors reading to or writing from backing store
    pass

class FileUpdateFailure(CatalogUpdateFailure):
    pass

class SampleUpdateFailure(CatalogUpdateFailure):
    pass

class MeasurementUpdateFailure(CatalogUpdateFailure):
    pass

class MeasurementStore(object):
    def __init__(self, mongodb, config):
        self.db = db_connection(mongodb)
        coll = config['collections']['measurements']
        if config['debug']:
            coll = coll + str(int(datetime.datetime.utcnow().timestamp()))
        self.coll = self.db[coll]
        self.coll.uuid_subtype = UUID_SUBTYPE
        self.base = config['base']
        self.store = config['root']

    def new_record(self, measurement):
        meas_id = measurement_id_from_properties(measurement)
        try:
            uid = catalog_uuid(meas_id)
            ts = datetime.datetime.utcnow()
        except Exception as exc:
            raise CatalogDataError(
                'Failed to auto-assign values for record', exc)
        extras = {'properties': {'created_date': ts,
                                 'modified_date': ts,
                                 'revision': 0},
                  'uuid': uid,
                  'id': meas_id}
        return dict_merge(copy.deepcopy(measurement), extras)

    def update_record(self, measurement):
        # Update properties
        measurement['properties']['modified_date'] = datetime.datetime.utcnow()
        measurement['properties']['revision'] += 1
        return measurement

    def create_update_measurement(self, measurement):
        # Does the record exist under the current filename
        # If yes, fetch it and update it
        #   Increment the revision and modified date
        # Otherwise, create a new instance
        #
        # Returns the record on success
        meas_id = measurement_id_from_properties(measurement)
        meas_uuid = catalog_uuid(meas_id)
        meas = self.coll.find_one({'uuid': meas_uuid})
        # TODO Genericize dict comparison
        # Compare the informative parts of the incoming and extant record
        # if isinstance(meas, dict):
        #     meas_dict = copy.deepcopy(meas)
        #     for p in ['properties', '_id', 'uuid']:
        #         try:
        #             meas_dict.pop(p)
        #         except KeyError:
        #             pass
        #     dc = dictcompare(meas_dict, meas)
        #     print(dc)
        #     diffs = sum(1 for d in dictcompare(
        #         meas_dict, meas) if d is not None)
        # Write the record
        if meas is None:
            try:
                newrec = self.new_record(measurement)
                self.coll.insert_one(newrec)
                return newrec
            except Exception:
                raise CatalogUpdateFailure('Failed to create new record')
        else:
            if meas_id != meas['id']:
                print('ids are different')
                try:
                    updated_rec = self.update_record(meas)
                    updated = self.coll.find_one_and_replace(
                        {'_id': meas['_id']},
                        updated_rec,
                        return_document=ReturnDocument.AFTER)
                    return updated
                except Exception as exc:
                    raise CatalogUpdateFailure(
                        'Failed to update existing record', exc)
            else:
                return meas

    def delete_record(self, measurement_id):
        '''Delete record by measurement.id'''
        try:
            meas_uuid = catalog_uuid(measurement_id)
            return self.coll.remove({'uuid': measurement_id})
        except Exception:
            raise CatalogUpdateFailure(
                'Failed to remove measurement {}'.format(meas_uuid))

    def normalize(self, filename):
        # Strip leading / and any combination of
        # /uploads/, /uploads, uploads/ since we
        # do not want to reference it
        if filename.startswith('/'):
            filename = filename[1:]
        if filename.startswith(self.store):
            filename = filename[len(self.store):]
        return filename


class SampleStore(object):
    def __init__(self, mongodb, config):
        self.db = db_connection(mongodb)
        coll = config['collections']['samples']
        if config['debug']:
            coll = coll + str(int(datetime.datetime.utcnow().timestamp()))
        self.coll = self.db[coll]
        self.coll.uuid_subtype = UUID_SUBTYPE
        self.base = config['base']
        self.store = config['root']

    # FIXME use generated uuid for database lookups
    def new_record(self, sample):
        try:
            uid = catalog_uuid(sample['id'])
            ts = datetime.datetime.utcnow()
        except Exception as exc:
            raise CatalogDataError('Failed to auto-assign values for record', exc)
        extras = {'properties': {'created_date': ts,
                                 'modified_date': ts,
                                 'revision': 0},
                  'uuid': uid}
        return dict_merge(copy.deepcopy(sample), extras)

    # FIXME use generated uuid for database lookups
    def update_record(self, sample):
        # Update properties
        sample['properties']['modified_date'] = datetime.datetime.utcnow()
        sample['properties']['revision'] += 1
        return sample

    def create_update_sample(self, sample):
        # Does the record exist under the current filename
        # If yes, fetch it and update it
        #   Increment the revision and modified date
        # Otherwise, create a new instance
        #
        # Returns the record on success

        rec = self.coll.find_one({'id': sample['id']})
        # TODO Genericize this
        # FIXME This is not working as intended
        # Compare the informative parts of the incoming and extant record
        diffs = 0
        # if isinstance(rec, dict):
        #     rec_dict = copy.deepcopy(rec)
        #     rec_dict.pop('properties')
        #     rec_dict.pop('_id')
        #     rec_dict.pop('uuid')
        #     diffs = sum(1 for d in dictcompare(
        #         rec_dict, sample) if d is not None)
        if rec is None:
            try:
                newrec = self.new_record(sample)
                self.coll.insert_one(newrec)
                return newrec
            except Exception:
                raise CatalogUpdateFailure('Failed to create new record')
        else:
            if diffs > 0:
                try:
                    filerec = self.update_record(rec)
                    updated = self.coll.find_one_and_replace(
                        {'_id': rec['_id']},
                        filerec,
                        return_document=ReturnDocument.AFTER)
                    return updated
                except Exception:
                    raise CatalogUpdateFailure('Failed to update existing record')
            else:
                return sample

    # FIXME use generated uuid for database lookups
    def delete_record(self, sample_id):
        '''Delete record by sample.id'''
        try:
            return self.coll.remove({'id': sample_id})
        except Exception:
            raise CatalogUpdateFailure('Failed to remove sample {}'.format(sample_id))

    def normalize(self, filename):
        # Strip leading / and any combination of
        # /uploads/, /uploads, uploads/ since we
        # do not want to reference it
        if filename.startswith('/'):
            filename = filename[1:]
        if filename.startswith(self.store):
            filename = filename[len(self.store):]
        return filename

class CatalogStore(object):
    def __init__(self, mongodb, config):
        self.db = db_connection(mongodb)
        coll = config['collections']['files']
        if config['debug']:
            coll = coll + str(int(datetime.datetime.utcnow().timestamp()))
        self.coll = self.db[coll]
        self.coll.uuid_subtype = UUID_SUBTYPE
        self.base = config['base']
        self.store = config['root']

    def get_fixity_properties(self, filename):
        absfilename = self.abspath(filename)
        properties = {}
        # file type
        try:
            ftype = get_filetype(absfilename)
            properties['inferred_file_type'] = ftype
        except Exception:
            pass
        # checksum
        try:
            cksum = compute_checksum(absfilename)
            properties['checksum'] = cksum
        except Exception:
            pass
        # size in bytes
        try:
            size = get_size_in_bytes(absfilename)
            properties['size_in_bytes'] = size
        except Exception:
            pass
        return properties

    def new_record(self, record):
        filename = record['filename']
        ts = datetime.datetime.utcnow()

        record['uuid'] = catalog_uuid(filename)
        # update attributes
        record['attributes'] = dict_merge(record.get('attributes', {}), {'lab': lab_from_path(filename)})
        # build up properties set if possible
        file_extras = {'created_date': ts, 'modified_date': ts, 'revision': 0, 'original_filename': filename}
        file_props = self.get_fixity_properties(filename)
        extras = dict_merge(file_extras, file_props)
        # amend existing properties
        props = dict_merge(record.get('properties', {}), extras)
        record['properties'] = props
        return record

    def update_record(self, record):
        # Update revision and timestamp
        filename = record['filename']
        record['uuid'] = catalog_uuid(filename)
        ts = datetime.datetime.utcnow()
        rev = record['properties'].get('revision', 0) + 1
        # build up properties if possible
        file_extras = {'modified_date': ts,
                       'revision': rev}
        # If updating a stub record, which means it might not have a created date
        if 'created_date' not in record['properties']:
            file_extras['created_date'] = ts
        # update fixity properties (in case they've changed due to re-upload etc)
        file_props = self.get_fixity_properties(filename)
        extras = dict_merge(file_extras, file_props)
        props = dict_merge(record.get('properties', {}), extras)
        record['properties'] = props
        return record

    def create_update_record(self, record):
        # Does the record exist under the current filename
        # If yes, fetch it and update it
        #   Increment the revision and modified date
        # Otherwise, create a new instance
        #
        # Returns the record on success
        filename = self.normalize(record['filename'])
        filerec = self.coll.find_one({'filename': filename})
        if filerec is None:
            try:
                newrec = self.new_record(record)
                self.coll.insert_one(newrec)
                return newrec
            except Exception:
                raise FileUpdateFailure('Create failed')
        else:
            try:
                filerec = self.update_record(filerec)
                updated = self.coll.find_one_and_replace(
                    {'_id': filerec['_id']},
                    filerec,
                    return_document=ReturnDocument.AFTER)
                return updated
            except Exception:
                raise FileUpdateFailure('Update failed')

    def delete_record(self, filename):
        '''Delete record by filename'''
        filename = self.normalize(filename)
        try:
            return self.coll.remove({'filename': filename})
        except Exception:
            raise FileUpdateFailure('Delete failed')

    def normalize(self, filename):
        # Strip leading / and any combination of
        # /uploads/, /uploads, uploads/ since we
        # do not want to reference it
        if filename.startswith('/'):
            filename = filename[1:]
        if filename.startswith(self.store):
            filename = filename[len(self.store):]
        return filename

    def abspath(self, filename):
        if filename.startswith('/'):
            filename = filename[1:]
        if filename.startswith(self.store):
            filename = filename[len(self.store):]
        return os.path.join(self.base, self.store, filename)

    def checkfile(self, filepath):
        '''Check if a filepath exists and is believed by the OS to be a file'''
        full_path = self.abspath(filepath)
        return os.path.isfile(full_path)

def dictcompare(a, b, section=None):
    # Used to compare database records as dicts
    # https://stackoverflow.com/a/48652830
    return [(c, d, g, section) if all(not isinstance(i, dict) for i in [d, g]) and d != g else None if all(not isinstance(i, dict) for i in [d, g]) and d == g else dictcompare(d, g, c) for [c, d], [h, g] in zip(a.items(), b.items())]


def catalog_uuid(filename):
    '''Returns a Binary encoded UUID5 in the prescribed namespace'''
    if filename.startswith('/'):
        filename = filename[1:]
    if filename.startswith(STORAGE_ROOT):
        filename = filename[len(STORAGE_ROOT):]
    #return str(uuid.uuid5(UUID_NAMESPACE, filename))
    return Binary(uuid.uuid5(UUID_NAMESPACE, filename).bytes, UUID_SUBTYPE)

def db_connection(settings):
    '''Get an active MongoDB connection'''
    try:
        uri = "mongodb://%s:%s@%s:%s" % (quote_plus(settings['username']),
                                         quote_plus(settings['password']),
                                         settings['host'],
                                         settings['port'])
        client = MongoClient(uri)
        db = client[settings['database']]
        return db
    except Exception as exc:
        raise CatalogDatabaseError('Unable to connect to database', exc)

def lab_from_path(filename):
    '''Infer experimental lab from a normalized upload path'''
    if filename.startswith('/'):
        raise CatalogDataError('"{}" is not a normalized path')
    path_els = splitall(filename)
    if path_els[0].lower() in Enumerations.LABPATHS:
        return path_els[0].lower()
    else:
        raise CatalogDataError('"{}" is not a known uploads path'.format(path_els[0]))

def labname_from_path(filename):
    '''Infer experimental lab from a normalized upload path'''
    if filename.startswith('/'):
        raise CatalogDataError('"{}" is not a normalized path')
    path_els = splitall(filename)
    if path_els[0].lower() in Enumerations.LABPATHS:
        return Mappings.LABPATHS.get(path_els[0].lower(), 'Unknown')
    else:
        raise CatalogDataError(
            '"{}" is not a known uploads path'.format(path_els[0]))

def measurement_id_from_properties(measurement, prefix=None):
    '''Returns a unique measurement identifier'''
    meas = copy.deepcopy(measurement)
    # Exclude uninformative keys
    for exclude in ['files', 'sample_ids']:
        try:
            meas.pop(exclude)
        except KeyError:
            pass
    kvlist = []
    if prefix is not None:
        kvlist.append(prefix.lower())
    for k in sorted(meas):
        if not isinstance(meas[k], (dict, list, tuple)):
            kvlist.append(k + ':' + slugify(meas[k]))
    joined = '|'.join(kvlist)
    return joined

# Reference: https://gist.github.com/angstwad/bf22d1822c38a92ec0a9#gistcomment-1986197
# FIXME: Does not merge lists
def dict_merge(dct, merge_dct, add_keys=True):
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    This version will return a copy of the dictionary and leave the original
    arguments untouched.
    The optional argument ``add_keys``, determines whether keys which are
    present in ``merge_dict`` but not ``dct`` should be included in the
    new dict.
    Args:
        dct (dict) onto which the merge is executed
        merge_dct (dict): dct merged into dct
        add_keys (bool): whether to add new keys
    Returns:
        dict: updated dict
    """
    #dct = dct.copy()
    dct = copy.deepcopy(dct)
    if not add_keys:
        merge_dct = {
            k: merge_dct[k]
            for k in set(dct).intersection(set(merge_dct))
        }
    for k, v in merge_dct.items():
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], collections.Mapping)):
            dct[k] = dict_merge(dct[k], merge_dct[k], add_keys=add_keys)
        else:
            dct[k] = merge_dct[k]
    return dct
