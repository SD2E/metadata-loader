import uuid

UUID = str(uuid.uuid4())

ALL = [
    ('/uploads/taconaut.txt', 'taconaut.txt', 'data-sd2e-community', 404, False, 'HTTPError'),
    ('/sample/tacc-cloud/572.png', '572.png', 'data-sd2e-community', 200, True, None),
    ('/sample/tacc-cloud/572.png', '/', 'data-sd2e-community', 0, False, 'IsADirectoryError')]
