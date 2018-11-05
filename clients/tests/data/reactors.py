import copy
import uuid

UUID = str(uuid.uuid4())

MSG = [
    ({'uuid': UUID, 'data': {}, 'token': 'mocktoken', 'event': 'run'}, True),
    ({'data': {}, 'token': 'mocktoken', 'event': 'run'}, False), ({'uuid': UUID, 'data': {}, 'token': 'mocktoken', 'event': 'run', 'extra': 'hello'}, True),
    ({'uuid': UUID, 'token': 'mocktoken', 'event': 'run', 'extra': 'hello'}, True)]

REACTORS_MSG = []
for msg, passtest in MSG:
    mes = ({'pipelinejob': msg}, passtest)
    REACTORS_MSG.append(mes)
    mes = ({'__options': {'pipelinejob': msg}}, passtest)
    REACTORS_MSG.append(mes)
    mes = ({'options': {'pipelinejob': msg}}, passtest)
    REACTORS_MSG.append(mes)
    mes = ({'option': {'pipelinejob': msg}}, False)
    REACTORS_MSG.append(mes)
