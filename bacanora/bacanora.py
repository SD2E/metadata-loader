import os
import json
import re
import sys
import tempfile
from pprint import pprint
from attrdict import AttrDict
from agavepy.agave import AgaveError
from requests.exceptions import HTTPError
from tenacity import retry, retry_if_exception_type
from tenacity import stop_after_delay
from tenacity import wait_exponential

from . import agaveutils
from .direct import direct_get, direct_put, DirectOperationFailed

PWD = os.getcwd()

@retry(retry=retry_if_exception_type(AgaveError), reraise=True, stop=stop_after_delay(8), wait=wait_exponential(multiplier=2, max=64))
def download(agave_client, file_to_download, local_filename, system_id='data-sd2e-community'):
    try:
        direct_get(file_to_download, local_filename,
                   system_id='data-sd2e-community')
    except DirectOperationFailed as exc:
        pprint(exc)
        # Download using Agave API call
        try:
            downloadFileName = os.path.join(PWD, local_filename)
            # Implements atomic download
            f = tempfile.NamedTemporaryFile('wb', delete=False)
            # with open(downloadFileName, 'wb') as f:
            rsp = agave_client.files.download(systemId=system_id,
                                              filePath=file_to_download)
            if isinstance(rsp, dict):
                raise AgaveError(
                    "Failed to download {}".format(file_to_download))
            for block in rsp.iter_content(2048):
                if not block:
                    break
                f.write(block)
            try:
                os.rename(f.name, downloadFileName)
            except Exception as rexc:
                raise OSError('Atomic rename failed after download', rexc)
            return downloadFileName
        except (HTTPError, AgaveError) as http_err:
            try:
                os.unlink(f.name)
            except Exception:
                pass
            if re.compile('404 Client Error').search(str(http_err)):
                raise HTTPError('404 Not Found') from http_err
            else:
                http_err_resp = agaveutils.process_agave_httperror(http_err)
                raise AgaveError(http_err_resp) from http_err

@retry(retry=retry_if_exception_type(AgaveError), reraise=True, stop=stop_after_delay(8), wait=wait_exponential(multiplier=2, max=64))
def upload(agave_client, file_to_upload, destination_path, system_id='data-sd2e-community', autogrant=False):
    try:
        direct_put(file_to_upload, destination_path, system_id='data-sd2e-community')
    except DirectOperationFailed as exc:
        pprint(exc)
        try:
            agave_client.files.importData(systemId=system_id,
                                          filePath=destination_path,
                                          fileToUpload=open(file_to_upload, 'rb'))
        except HTTPError as h:
            http_err_resp = agaveutils.process_agave_httperror(h)
            raise Exception(http_err_resp)
        except Exception as e:
            raise AgaveError(
                "Error uploading {}: {}".format(file_to_upload, e))
    if autogrant:
        return grant(agave_client, destination_path)
    else:
        return True

@retry(stop=stop_after_delay(180), wait=wait_exponential(multiplier=2, max=64))
def grant(agave_client, pems_grant_target, system_id, username='world', permission='READ'):
    try:
        pemBody = {'username': username,
                   'permission': permission,
                   'recursive': False}
        agave_client.files.updatePermissions(systemId=system_id,
                                             filePath=pems_grant_target,
                                             body=pemBody)
    except HTTPError as h:
        http_err_resp = agaveutils.process_agave_httperror(h)
        raise Exception(http_err_resp)
    except Exception as e:
        raise AgaveError(
            "Error setting permissions on {}: {}".format(pems_grant_target, e))
    return True
