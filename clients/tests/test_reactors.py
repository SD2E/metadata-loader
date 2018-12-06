import pytest
from . import reactors
from . import data
from .fixtures.reactor import reactor, actor_id, abaco_message

def test_reactor_fixture(reactor, actor_id, abaco_message):
    reactor.send_message(actor_id, abaco_message)

def test_init_reactors(reactor):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is False:
            with pytest.raises(reactors.PipelineJobClientError) as exc:
                reactors.ReactorsPipelineJobClient(reactor, msg)
            assert 'job details' in exc.value.args[0]
        else:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            assert getattr(cli, 'uuid') is not None

def test_setup_reactor(reactor):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.setup()

def test_handler_run_string(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.run('helo')
            captured = capsys.readouterr()
            assert "{'message': 'helo'}" in captured.out

def test_handler_run_dict(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.run({'greeting': 'helo'})
            captured = capsys.readouterr()
            assert "{'greeting': 'helo'}" in captured.out

def test_handler_run_empty(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.run()
            captured = capsys.readouterr()
            assert "'data': {}" in captured.out

def test_handler_run_none(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.run(None)
            captured = capsys.readouterr()
            assert "{'message': 'None'}" in captured.out

def test_handler_no_revert(reactor):
    """Cannot call run or update after fail or finish"""
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            with pytest.raises(reactors.PipelineJobClientError) as exc:
                cli = reactors.ReactorsPipelineJobClient(reactor, msg)
                cli.run('helo')
                cli.fail('fail')
                cli.run('helo again')
            assert 'terminal state' in str(exc.value)

def test_handler_update_string(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.update('helo')
            captured = capsys.readouterr()
            assert "{'message': 'helo'}" in captured.out

def test_handler_update_dict(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.update({'greeting': 'helo'})
            captured = capsys.readouterr()
            assert "{'greeting': 'helo'}" in captured.out

def test_handler_update_none(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.update(None)
            captured = capsys.readouterr()
            assert "{'message': 'None'}" in captured.out

def test_handler_finish_string(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.run()
            cli.finish('helo')
            captured = capsys.readouterr()
            assert "{'message': 'helo'" in captured.out

def test_handler_finish_dict(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.run()
            cli.finish({'greeting': 'helo'})
            captured = capsys.readouterr()
            assert "{'greeting': 'helo'" in captured.out

def test_handler_finish_empty(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.run()
            cli.finish()
            captured = capsys.readouterr()
            assert "{'message': 'Unspecified'" in captured.out

def test_handler_finish_none(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.run()
            cli.finish(None)
            captured = capsys.readouterr()
            assert "{'message': 'None'" in captured.out

def test_handler_fail_string(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.run()
            cli.fail('helo')
            captured = capsys.readouterr()
            assert "{'message': 'helo'" in captured.out

def test_handler_fail_dict(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.run()
            cli.fail({'greeting': 'helo'})
            captured = capsys.readouterr()
            assert "{'greeting': 'helo'" in captured.out

def test_handler_fail_empty(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.run()
            cli.fail()
            captured = capsys.readouterr()
            assert "{'message': 'Unspecified'" in captured.out

def test_handler_fail_none(reactor, capsys):
    for msg, passtest in data.reactors.REACTORS_MSG:
        if passtest is True:
            cli = reactors.ReactorsPipelineJobClient(reactor, msg)
            cli.run()
            cli.fail(None)
            captured = capsys.readouterr()
            assert "{'message': 'None'" in captured.out
