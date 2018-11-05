from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import *
from future import standard_library
standard_library.install_aliases()

import pytest
import logging
import random
from pprint import pprint
from attrdict import AttrDict
from .agave import agave, credentials
from .abaco import get_id

@pytest.fixture(scope='session')
def actor_id(scope='session'):
    return get_id()

@pytest.fixture(scope='session')
def abaco_message(scope='session'):
    mes = {'text': 'fixture text'}
    return mes

@pytest.fixture(scope='session')
def reactor():

    class Reactor(AttrDict):
        """Minimal mocking class for Abaco Reactor"""

        def __init__(self, *args):
            super(Reactor, self).__init__(*args)
            self.uid = get_id()
            self.execid = get_id()
            self.nickname = 'mocking-reactor'
            self.client = 'Agave'
            #self.client = agave(credentials())
            self.settings = AttrDict({'pipelines':
                                      {'job_manager_id': get_id()}})
            FORMAT = '%(asctime)-15s %(message)s'
            logging.basicConfig(format=FORMAT)
            self.logger = logging.getLogger(self.nickname)

        def send_message(self, actorId, message, environment={}, ignoreErrors=True, senderTags=True, retryMaxAttempts=5, retryDelay=1, sync=False):
            print('actorId', actorId)
            print('message', message)
            print('environment', environment)
            return get_id()

        def elapsed(self):
            return (1000 * random.random())

        def to_dict(self):
            return dict(self)

    r = Reactor()
    return r
