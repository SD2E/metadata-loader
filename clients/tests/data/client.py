import uuid

UUID = str(uuid.uuid4())

MESSAGE_INIT = [
    ({'uuid': UUID, 'data': {}, 'token': 'def', 'event': 'run'}, True),
    ({'data': {}, 'token': 'def', 'event': 'run'}, False), ({'uuid': UUID, 'data': {}, 'token': 'def', 'event': 'run', 'extra': 'hello'}, True),
    ({'uuid': UUID, 'token': 'def', 'event': 'run', 'extra': 'hello'}, True)]

CLIENT_INIT = MESSAGE_INIT
