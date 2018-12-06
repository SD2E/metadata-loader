import pytest
from . import client
from . import data

def test_init_message():
    for msg, passtest in data.client.MESSAGE_INIT:
        if passtest is False:
            with pytest.raises(client.PipelineJobClientError) as exc:
                client.PipelineJobUpdateMessage(**msg)
            assert 'is mandatory' in exc.value.args[0]
        else:
            mes = client.PipelineJobUpdateMessage(**msg)
            assert getattr(mes, 'uuid') == msg['uuid']

def test_init_client():
    for msg, passtest in data.client.CLIENT_INIT:
        if passtest is False:
            with pytest.raises(client.PipelineJobClientError) as exc:
                client.PipelineJobClient(**msg)
            assert 'is mandatory' in exc.value.args[0]
        else:
            cli = client.PipelineJobClient(**msg)
            assert getattr(cli, 'uuid') == msg['uuid']

def test_setup_client():
    for msg, passtest in data.client.CLIENT_INIT:
        if passtest is True:
            cli = client.PipelineJobClient(**msg)
            cli.setup()

def test_no_events_without_setup():
    """Must call setup() before handling events"""
    for msg, passtest in data.client.CLIENT_INIT:
        if passtest is True:
            cli = client.PipelineJobClient(**msg)
            with pytest.raises(client.PipelineJobClientError):
                cli.run()
            cli.setup().run()
