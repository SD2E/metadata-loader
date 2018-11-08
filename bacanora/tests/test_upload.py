import pytest
from .fixtures.agave import agave, credentials
from . import data

from requests import HTTPError
from tenacity import stop_after_delay

from .. import bacanora

def test_uploads(agave):
    for file_path, dest_file, system_id, code, pass_test, exc in data.upload.ALL:
        if pass_test is False:
            with pytest.raises(Exception) as exc:
                bacanora.upload(agave, file_path, dest_file, system_id)
            assert str(code) in str(exc)
        else:
            resp = bacanora.upload(agave, file_path, dest_file, system_id)
            assert resp is True
