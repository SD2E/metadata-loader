from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import *
from future import standard_library
standard_library.install_aliases()

import json
from attrdict import AttrDict

__all__ = ['PipelineJobClient',
           'PipelineJobUpdateMessage', 'PipelineJobClientError']


class PipelineJobClientError(Exception):
    pass


class PipelineJobClient(object):
    PARAMS = [('uuid', True, 'uuid', None),
              ('token', True, 'token', None),
              ('manager', False, '__manager', None),
              ('actor_id', False, 'actor_id', None),
              ('pipeline_uuid', False, 'pipeline_uuid', None),
              ('data', False, 'data', None),
              ('archive_system', False, 'archive_system', None),
              ('abaco_nonce', False, '__nonce', None),
              ('path', False, 'path', None),
              ('callback', False, 'callback', None),
              ('status', False, 'status', None),
              ('permissive', False, '_permissive', False)]

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
        self._setup = False

    def setup(self, *args, **kwargs):
        setattr(self, '_setup', True)
        self._check_setup()
        return self

    def _check_state(self):
        try:
            setup = self._check_setup()
            term = self._check_term()
            return (setup and term)
        except PipelineJobClientError as perr:
            raise PipelineJobClientError(perr)

    def _check_setup(self):
        if getattr(self, '_setup'):
            return True
        else:
            raise PipelineJobClientError('Call setup() before doing any state management')

    def _check_term(self):
        if getattr(self, 'status') not in ('FAILED', 'FINISHED'):
            return True
        else:
            raise PipelineJobClientError('Client has been set to terminal state. No further update events can be handled.')

    def run(self, *args, **kwargs):
        self._check_state()
        setattr(self, 'status', 'RUNNING')
        return self

    def update(self, *args, **kwargs):
        self._check_state()
        setattr(self, 'status', 'RUNNING')
        return self

    def finish(self, *args, **kwargs):
        self._check_state()
        setattr(self, 'status', 'FINISHED')
        return self

    def fail(self, *args, **kwargs):
        self._check_state()
        setattr(self, 'status', 'FAILED')
        return self


class PipelineJobUpdateMessage(AttrDict):
    PARAMS = [('uuid', True, 'uuid', None),
              ('data', False, 'data', {}),
              ('token', True, 'token', None),
              ('event', True, 'event', 'update')]

    def __init__(self, **kwargs):
        super(PipelineJobUpdateMessage, self).__init__()
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
