import json
import copy
from slugify import slugify
import datetime
from .mongo import db_connection, ReturnDocument, UUID_SUBTYPE
from .utils import catalog_uuid, current_time, time_stamp, validate_file_to_schema
from .dicthelpers import data_merge, dict_compare, filter_dict, json_diff, data_merge_diff
from .constants import Constants, Mappings, Enumerations
from .exceptions import CatalogError

class LogStoreError(CatalogError):
    pass

class LogStore(object):
    def __init__(self, mongodb, config):
        self.db = db_connection(mongodb)
        coll = config['collections']['updates']
        if config['debug']:
            coll = '_'.join([coll, str(time_stamp(rounded=True))])
        self.name = coll
        self.coll = self.db[coll]

    def append(self, collection_name, uuid, diff):
        """Write a JSON diff to the update log, extended with source
        collection and uuid.
        """
        ts = current_time()
        rec = {'created_date': ts, 'ref': {'collection': collection_name, 'uuid': uuid}, 'diff': diff}
        try:
            result = self.coll.insert_one(rec)
            return self.coll.find_one({'_id': result.inserted_id})
        except Exception as exc:
            raise CatalogError('failed to log update', exc)
