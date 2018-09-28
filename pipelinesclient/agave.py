from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *

from .client import PipelineJobClient, PipelineJobUpdateMessage, PipelineJobClientError

class AgavePipelineJobClient(PipelineJobClient):
    raise NotImplementedError('Agave Jobs support is forthcoming')
