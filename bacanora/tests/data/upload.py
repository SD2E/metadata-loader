import os
import uuid


UUID = str(uuid.uuid4())
THIS = os.path.abspath(__file__)
DIR = os.path.dirname(THIS)

ALL = [
    (os.path.join(DIR, 'taconaut.txt'), '/sample/tacc-cloud', 'data-sd2e-community', 200, True, None),
    (os.path.join(DIR, '572.png'), '/sample/tacc-cloud', 'data-sd2e-community', 200, True, None),
    (os.path.join(DIR, 'taconaut.txt'), '/nonexistent/path/', 'data-sd2e-community', 404, False, 'HTTPError')]
