import os
import json
import sys
from attrdict import AttrDict
from agavepy.agave import AgaveError
from requests.exceptions import HTTPError
from reactors.runtime import agaveutils
from tenacity import retry
from tenacity import stop_after_delay
from tenacity import wait_exponential


@retry(stop=stop_after_delay(300), wait=wait_exponential(multiplier=2, max=64))
def upload(robj, file_to_upload, destination_abspath, system_id='data-sd2e-community'):
    try:
        robj.client.files.importData(systemId=system_id,
                                     filePath=destination_abspath,
                                     fileToUpload=open(file_to_upload, 'rb'))
        grant_pems(robj, os.path.join(destination_abspath,
                                    file_to_upload), system_id, 'world', 'READ')
    except HTTPError as h:
        http_err_resp = agaveutils.process_agave_httperror(h)
        raise Exception(http_err_resp)
    except Exception as e:
        raise AgaveError(
            "Error uploading {}: {}".format(file_to_upload, e))
    return True


@retry(stop=stop_after_delay(300), wait=wait_exponential(multiplier=2, max=64))
def download(robj, file_to_download, local_filename, system_id='data-sd2e-community'):
    try:
        agaveutils.agave_download_file(
            agaveClient=robj.client,
            agaveAbsolutePath=file_to_download,
            systemId=system_id,
            localFilename=local_filename)
    except HTTPError as h:
        http_err_resp = agaveutils.process_agave_httperror(h)
        raise Exception(http_err_resp)
    except Exception as exc:
        raise AgaveError(
            "Error downloading {}".format(file_to_download), exc)


@retry(stop=stop_after_delay(300), wait=wait_exponential(multiplier=2, max=64))
def grant_pems(robj, pems_grant_target, system_id, username='world', permission='READ'):
    try:
        pemBody = {'username': username,
                   'permission': permission,
                   'recursive': False}
        robj.client.files.updatePermissions(systemId=system_id,
                                            filePath=pems_grant_target,
                                            body=pemBody)
    except HTTPError as h:
        http_err_resp = agaveutils.process_agave_httperror(h)
        raise Exception(http_err_resp)
    except Exception as e:
        raise AgaveError(
            "Error setting permissions on {}: {}".format(pems_grant_target, e))
    return True
