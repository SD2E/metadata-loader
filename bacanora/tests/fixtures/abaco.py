
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *

import uuid
from hashids import Hashids

SALT = 'ZC~>dC=#^W;`m2*e'

__all__ = ["generate", "validate", "mock"]

def generate():
    return get_id()

def validate(text_string, permissive=False):
    result = is_hashid(text_string)
    if result is True:
        return result
    else:
        if permissive is False:
            raise ValueError(
                '{} is not a valid abaco hashid'.format(text_string))
        else:
            return False

def mock():
    """Return an identifer that looks like an Abaco hashid but
    will not be guaranteed to validate"""
    return get_id(salt=SALT)

def get_id(salt=SALT):
    '''Generate a new random hash id'''
    hashids = Hashids(salt=salt)
    _uuid = uuid.uuid1().int >> 64
    return hashids.encode(_uuid)

def is_hashid(identifier):
    '''Tries to validate a HashId'''
    hashids = Hashids(salt=SALT)
    dec = hashids.decode(identifier)
    if len(dec) > 0:
        return True
    else:
        return False
