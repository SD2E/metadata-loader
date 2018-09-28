from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import *
from future import standard_library
standard_library.install_aliases()

from .client import PipelineJobClient, PipelineJobUpdateMessage, PipelineJobClientError


class ReactorsPipelineJobClient(PipelineJobClient):
    def __init__(self, reactor, reactor_msg, **kwargs):
        super(ReactorsPipelineJobClient, self).__init__(**kwargs)
        jobconf = {}
        try:
            if 'pipelinejob' in reactor_msg:
                pipejobconf = reactor_msg['pipelinejob']
            elif '__options' in reactor_msg:
                pipejobconf = reactor_msg['__options']['pipelinejob']
            elif 'options' in reactor_msg:
                pipejobconf = reactor_msg['options']['pipelinejob']
            else:
                raise KeyError('Message is missing required keys')
            jobconf = {
                'uuid': pipejobconf['uuid'],
                'token': pipejobconf['token'],
                'data': pipejobconf.get('data', {})}
        except KeyError as kexc:
            raise PipelineJobClientError(
                'Failed to find job details in message', kexc)
        super(ReactorsPipelineJobClient, self).__init__(**jobconf)
        self.__reactor = reactor
        self.__manager = reactor.settings.pipelines.job_manager_id

    def _message(self, message, permissive=True):
        """Private wrapper for sending update message to the
        PipelineJobsManager Reactor. Failures are logged by default
        but can be set to raise an exception by setting permissive
        to False"""
        abaco_message = PipelineJobUpdateMessage(**message).to_dict()
        try:
            self.__reactor.send_message(
                self.__manager, abaco_message, retryMaxAttempts=3)
            return True
        except Exception as exc:
            self.__reactor.logger.warning(
                'Failed to update PipelineJob: {}'.format(exc))
            if permissive:
                return False
            else:
                raise PipelineJobClientError(exc)

    def run(self, message={}, **kwargs):
        super(ReactorsPipelineJobClient, self).run(**kwargs)
        data = self.render(message)
        job_message = kwargs.update({'data': data, 'event': 'run'})
        return self._message(job_message)

    def update(self, message={}, **kwargs):
        super(ReactorsPipelineJobClient, self).update(**kwargs)
        data = self.render(message)
        job_message = kwargs.update({'data': data, 'event': 'update'})
        return self._message(job_message)

    def fail(self, message='Unspecified', **kwargs):
        super(ReactorsPipelineJobClient, self).fail(**kwargs)
        data = self.render(message, 'cause')
        data['elapsed'] = str(self.__reactor.elapsed()) + ' usec'
        job_message = kwargs.update({'data': data, 'event': 'fail'})
        return self._message(job_message)

    def finish(self, message='Unspecified', **kwargs):
        super(ReactorsPipelineJobClient, self).fail(**kwargs)
        if isinstance(message, dict):
            data = message
        else:
            data = {'message': str(message)}
        data['elapsed'] = str(self.__reactor.elapsed()) + ' usec'
        job_message = kwargs.update({'data': data, 'event': 'finish'})
        return self._message(job_message)

    def render(self, message, key='message'):
        # TODO: Add a custom renderer for other types
        data = {}
        if isinstance(message, dict):
            data = message
        else:
            data = {key: str(message)}
        return data
