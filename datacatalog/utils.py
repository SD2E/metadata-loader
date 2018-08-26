import uuid
import datetime
from bson.binary import Binary, UUID_SUBTYPE, OLD_UUID_SUBTYPE
from .constants import Constants


def current_time():
    """Blessed method for getting current time"""
    return datetime.datetime.utcnow()

def time_stamp(dt=None, rounded=False):
    """Blessed method to get a timestamp"""
    if dt is None:
        dt = current_time()
    if rounded:
        return int(dt.timestamp())
    else:
        return dt.timestamp()

def catalog_uuid(filename, binary=False):
    """Returns a UUID5 in the prescribed namespace
    This function will either a text UUID or a BSON-encoded binary UUID,
    depending on the optional value ``binary``.
    Args:
        filename (string) nominally, a file path, but can be any string
        binary (bool): whether to encode result as BSON binary
    Returns:
        new_uuid: a computable UUID in string or binary-encoded form
    """
    if filename.startswith('/'):
        filename = filename[1:]
    if filename.startswith(Constants.STORAGE_ROOT):
        filename = filename[len(Constants.STORAGE_ROOT):]
    new_uuid = uuid.uuid5(Constants.UUID_NAMESPACE, filename)
    if binary is False:
        return str(new_uuid)
    else:
        return Binary(new_uuid.bytes, UUID_SUBTYPE)


