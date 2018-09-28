from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *

import json
from attrdict import AttrDict

class PipelineJobClientError(Exception):
    pass

class PipelineJobClient(object):
    PARAMS = [('uuid', True, 'uuid', None),
        ('manager', True, '__manager', None),
        ('token', True, 'token', None),
        ('actor_id', False, 'actor_id', None),
        ('pipeline_uuid', False, 'pipeline_uuid', None),
        ('data', False, 'data', None),
        ('archive_system', False, 'archive_system', None),
        ('abaco_nonce', False, '__nonce', None),
        ('path', False, 'path', None),
        ('callback', False, 'callback', None),
        ('status', False, 'status', None)]
    def __init__(self, *args, **kwargs):
        for param, mandatory, attr, default in self.PARAMS:
            try:
                value = (kwargs[param] if mandatory
                    else kwargs.get(param, default))
            except KeyError:
                raise PipelineJobClientError(
                    'parameter "{}" is mandatory'.format(param))
            setattr(self, attr, value)
        self.create = None
        self.cancel = None
    def setup(self, *args, **kwargs):
        return self
    def run(self, *args, **kwargs):
        self.status = 'RUNNING'
        return self
    def update(self, *args, **kwargs):
        self.status = 'RUNNING'
        return self
     def finish(self, *args, **kwargs):
        self.status = 'FINISHED'
        return self
    def fail(self, *args, **kwargs):
        self.status = 'FAILED'
        return self

class PipelineJobUpdateMessage(AttrDict):
    PARAMS = [('uuid', True, 'uuid', None),
        ('data', False, 'data', {}),
        ('token', True, 'token', None),
        ('event', True, 'event', 'update')]
    def __init__(self, **kwargs):
        for param, mandatory, attr, default in self.PARAMS:
            try:
                value = (kwargs[param] if mandatory
                    else kwargs.get(param, default))
            except KeyError:
                raise PipelineJobClientError(
                    'parameter "{}" is mandatory'.format(param))
            setattr(self, attr, value)
    def to_dict(self):
        return dict(self)
    def to_json(self, **kwargs):
        return json.dumps(self.to_dict(), **kwargs)
