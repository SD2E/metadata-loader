from ..jobs import JobStore, JobCreateFailure, JobUpdateFailure

class PipelineJob():
    ARGS = ['pipeline_uuid',
            'lab_name',
            'experiment_reference',
            'measurement_id']
    def __init__(self, **kwargs):
        pass

class JobManager(JobStore):
    pass

    def prepare(self, **kwargs):
        job = PipelineJob(**kwargs)
        return job

