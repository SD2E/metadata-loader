import os
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
        raise UnknownRuntime('Not a Bacanora-enabled runtime')

def direct_get(file_to_download, local_filename, system_id='data-sd2e-community'):
    try:
        environ = detect_runtime()
        prefix = get_prefix(system_id, environ)
        full_path = os.path.join(prefix, file_to_download)
        if os.path.exists(full_path):
            shutil.copy(os.path.join(prefix, file_to_download), local_filename)
        else:
            raise DirectOperationFailed('Unable to access file')
    except UnknownRuntime as uexc:
        raise UnknownRuntime(uexc)
    except UnknownStorageSystem as ustor:
        raise UnknownStorageSystem(ustor)

