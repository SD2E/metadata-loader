from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import *
from future import standard_library
standard_library.install_aliases()

from .client import PipelineJobClient, PipelineJobUpdateMessage, PipelineJobClientError


class JenkinsPipelineJobClient(PipelineJobClient):
    raise NotImplementedError('Jenkins support is forthcoming')
