import os
import pytest
from .fixtures.agave import agave, credentials
from . import data

from requests import HTTPError
from tenacity import stop_after_delay

from .. import bacanora

def test_downloads(agave):
    for file_path, dest_file, system_id, code, pass_test, exc in data.download.ALL:
        if pass_test is False:
            with pytest.raises(Exception) as exc:
                bacanora.download(agave, file_path, dest_file, system_id)
            assert str(exc) in str(exc)
        else:
            resp = bacanora.download(agave, file_path, dest_file, system_id)
            assert dest_file in resp
            os.unlink(dest_file)
