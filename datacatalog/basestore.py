import json
import copy
from slugify import slugify
import datetime
from .mongo import db_connection, ReturnDocument, UUID_SUBTYPE
from .logstore import LogStore, LogStoreError
from .utils import catalog_uuid, current_time, time_stamp, validate_file_to_schema
from .dicthelpers import data_merge, dict_compare, filter_dict, json_diff, data_merge_diff
from .constants import Constants, Mappings, Enumerations
#from .exceptions import *
from .posixhelpers import *

class BaseStore(object):
    def __init__(self, mongodb, config):
        self.db = db_connection(mongodb)
        self.base = config['base']
        self.store = config['root']
        self.agave_system = config['storage_system']
        self.coll = None
        self.name = None
        self.difflog = LogStore(mongodb, config)

    def log(self, uuid, diff):
        try:
            self.difflog.append(self.name, uuid, diff)
        except Exception as exc:
            raise LogStoreError(exc)

    def query(self, query={}):
        try:
            if not isinstance(query, dict):
                query = json.loads(query)
        except Exception as exc:
            raise CatalogQueryError('query was not resolvable as dict', exc)
        try:
            return self.coll.find(query)
        except Exception as exc:
            raise CatalogQueryError('query failed')

    def delete(self, uuid):
        '''Delete record by uuid'''
        try:
            return self.coll.remove({'uuid': uuid})
        except Exception:
            raise CatalogUpdateFailure('Delete failed')

    def abspath(self, filename):
        if filename.startswith('/'):
            filename = filename[1:]
        if filename.startswith(self.store):
            filename = filename[len(self.store):]
        return os.path.join(self.base, self.store, filename)

    def normalize(self, filename):
        # Strip leading / and any combination of
        # /uploads/, /uploads, uploads/ since we
        # do not want to reference it
        if filename.startswith('/'):
            filename = filename[1:]
        if filename.startswith(self.store):
            filename = filename[len(self.store):]
        return filename

    def to_agave_uri(self, filename):
        full_path = os.path.join(self.store, filename)
        return 'agave://' + self.agave_system + '/' + full_path


class CatalogError(Exception):
    pass


class CatalogUpdateFailure(CatalogError):
    # Errors arising when the Data Catalog can't be updated
    pass


class CatalogDataError(CatalogError):
    # Errors arising from computing or validating metadata
    pass


def lab_from_path(filename):
    '''Infer experimental lab from a normalized upload path'''
    if filename.startswith('/'):
        raise CatalogDataError('"{}" is not a normalized path')
    path_els = splitall(filename)
    if path_els[0].lower() in Enumerations.LABPATHS:
        return path_els[0].lower()
    else:
        raise CatalogDataError(
            '"{}" is not a known uploads path'.format(path_els[0]))

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