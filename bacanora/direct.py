import os
import datetime
import shutil

class DirectOperationFailed(Exception):
    pass

class UnknownRuntime(DirectOperationFailed):
    pass

class UnknownStorageSystem(DirectOperationFailed):
    pass

class StorageSystems():
    prefixes = {'data-sd2e-community': {'hpc': '/work/projects/SD2E-Community/prod/data',
                                        'abaco': '/work/projects/SD2E-Community/prod/data',
                                        'jupyter': os.path.join(
                                            os.path.expanduser('~'), 'sd2e-community')}}

def get_prefix(storage_system, environment):
    try:
        return StorageSystems.prefixes[storage_system][environment]
    except KeyError:
        raise UnknownStorageSystem(
            'Bacanora mapping for {} is not defined'.format(storage_system))

def detect_runtime():
    if 'REACTORS_VERSION' in os.environ:
        return 'abaco'
    elif 'JUPYTERHUB_USER' in os.environ:
        return 'jupyter'
    elif 'TACC_DOMAIN' in os.environ:
        return 'hpc'
    else:
        return 'abaco'
        # raise UnknownRuntime('Not a Bacanora-enabled runtime')

def direct_get(file_to_download, local_filename, system_id='data-sd2e-community'):
    try:
        environ = detect_runtime()
        prefix = get_prefix(system_id, environ)
        if file_to_download.startswith('/'):
            file_to_download = file_to_download[1:]
        full_path = os.path.join(prefix, file_to_download)
        temp_local_filename = local_filename + '-' + str(int(datetime.datetime.utcnow().timestamp()))
        print('DIRECT_GET: {}'.format(full_path))
        if os.path.exists(full_path):
            shutil.copy(os.path.join(prefix, file_to_download), temp_local_filename)
        else:
            raise DirectOperationFailed('Failed to download file')
        try:
            os.rename(temp_local_filename, local_filename)
        except Exception as rexc:
            raise DirectOperationFailed('Atomic rename failed after download', rexc)
    except UnknownRuntime as uexc:
        raise UnknownRuntime(uexc)
    except UnknownStorageSystem as ustor:
        raise UnknownStorageSystem(ustor)

def direct_put(file_to_upload, destination_path, system_id='data-sd2e-community'):
    try:
        environ = detect_runtime()

        prefix = get_prefix(system_id, environ)
        if destination_path.startswith('/'):
            destination_path = destination_path[1:]
        full_dest_path = os.path.join(prefix, destination_path)

        filename = os.path.basename(file_to_upload)
        filename_atomic = filename + '-' + str(int(datetime.datetime.utcnow().timestamp()))
        atomic_dest_path = os.path.join(full_dest_path, filename_atomic)
        final_dest_path = os.path.join(full_dest_path, filename)
        print('DIRECT_PUT: {}'.format(atomic_dest_path))
        if os.path.exists(full_dest_path):
            shutil.copy(file_to_upload, atomic_dest_path)
        else:
            raise DirectOperationFailed('Failed to upload file')
        try:
            os.rename(atomic_dest_path, final_dest_path)
        except Exception as exc:
            raise DirectOperationFailed('Atomic rename failed after upload', exc)
    except UnknownRuntime as uexc:
        raise UnknownRuntime(uexc)
    except UnknownStorageSystem as ustor:
        raise UnknownStorageSystem(ustor)
