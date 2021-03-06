import asyncio
import functools
import json
import os
import random
import requests
import subprocess
import time

from asyncio_extras import async_contextmanager
from async_generator import yield_
from contextlib import contextmanager
from juju.controller import Controller
from juju.model import Model
from juju.errors import JujuError
from .logger import log_calls, log_calls_async
from subprocess import check_output, check_call


@log_calls
def fetch_field_agent_and_run(log_dir):
    url = 'https://raw.githubusercontent.com/juju-solutions/cdk-field-agent/master/collect.py'
    response = requests.get(url)
    path = log_dir + '/collect.py'
    with open(path, 'wb') as f:
        f.write(response.content)
    os.chmod(path, 0o755)
    subprocess.check_call(['./collect.py'], cwd=log_dir)


@log_calls_async
async def add_model_via_cli(controller, name, config, force_cloud=''):
    ''' Add a Juju model using the CLI.

    Workaround for https://github.com/juju/python-libjuju/issues/122
    '''
    cmd = ['juju', 'add-model', name]
    if not force_cloud == '':
        cmd += [force_cloud]
    controller_name = controller.controller_name
    if controller_name:
        cmd += ['-c', controller_name]
    for k, v in config.items():
        cmd += ['--config', k + '=' + json.dumps(v)]
    await asyncify(check_call)(cmd)
    model = Model()
    if controller_name:
        await model.connect_model(controller_name + ':' + name)
    else:
        await model.connect_model(name)
    return model


@contextmanager
def timeout_for_current_task(timeout):
    ''' Create a context with a timeout.

    If the context body does not finish within the time limit, then the current
    asyncio task will be cancelled, and an asyncio.TimeoutError will be raised.
    '''
    loop = asyncio.get_event_loop()
    task = asyncio.Task.current_task()
    handle = loop.call_later(timeout, task.cancel)
    try:
        yield
    except asyncio.CancelledError:
        raise asyncio.TimeoutError('Timed out after %f seconds' % timeout)
    finally:
        handle.cancel()


@async_contextmanager
async def captured_fail_logs(model, log_dir):
    ''' Create a context that captures debug info when any exception is raised.
    '''
    try:
        await yield_()
    except:
        await asyncify(fetch_field_agent_and_run)(log_dir)
        raise


@log_calls
def apply_profile(model_name):
    '''
    Apply the lxd profile
    Args:
        model_name: the model name

    Returns: lxc profile edit output

    '''
    here = os.path.dirname(os.path.abspath(__file__))
    profile = os.path.join(here, "templates", "lxd-profile.yaml")
    lxc_aa_profile="lxc.aa_profile"
    cmd ='lxc --version'
    version = check_output(['bash', '-c', cmd])
    if version.decode('utf-8').startswith('3.'):
        lxc_aa_profile="lxc.apparmor.profile"
    cmd ='sed -e "s/##MODEL##/{0}/" -e "s/##AA_PROFILE##/{1}/" "{2}" | ' \
         'lxc profile edit "juju-{0}"'.format(model_name, lxc_aa_profile, profile)
    return check_output(['bash', '-c', cmd])


@async_contextmanager
async def temporary_model(log_dir, timeout=14400, force_cloud=''):
    ''' Create and destroy a temporary Juju model named cdk-build-upgrade-*.

    This is an async context, to be used within an `async with` statement.
    '''
    with timeout_for_current_task(timeout):
        controller = Controller()
        await controller.connect_current()
        model_name = 'cdk-build-upgrade-%d' % random.randint(0, 10000)
        model_config = {'test-mode': True}
        model = await add_model_via_cli(controller, model_name, model_config, force_cloud)
        cloud = await controller.get_cloud()
        if cloud == 'localhost':
            await asyncify(apply_profile)(model_name)
        try:
            async with captured_fail_logs(model, log_dir):
                await yield_(model)
        finally:
            await model.disconnect()
            await controller.destroy_model(model_name)
            await controller.disconnect()


def assert_no_unit_errors(model):
    for unit in model.units.values():
        assert unit.workload_status != 'error'
        assert unit.agent_status != 'failed'
        assert unit.agent_status != 'lost'


def all_units_ready(model):
    ''' Returns True if all units are 'active' and 'idle', False otherwise. '''
    for unit in model.units.values():
        if unit.workload_status != 'active':
            return False
        if unit.agent_status != 'idle':
            return False
    return True


@log_calls_async
async def wait_for_ready(model):
    ''' Wait until all units are 'active' and 'idle'. '''
    # FIXME: We might need to wait for more than just unit status.
    #
    # Subordinate units, for example, don't come into existence until after the
    # principal unit has settled.
    #
    # If you see problems where this didn't wait long enough, it's probably
    # that.
    while not all_units_ready(model):
        assert_no_unit_errors(model)
        await asyncio.sleep(1)


def asyncify(f):
    ''' Convert a blocking function into a coroutine '''
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        partial = functools.partial(f, *args, **kwargs)
        return await loop.run_in_executor(None, partial)
    return wrapper


@log_calls_async
async def upgrade_charms(model, channel):
    for app in model.applications.values():
        try:
            await app.upgrade_charm(channel=channel)
        except JujuError as e:
            if "already running charm" not in str(e):
                raise
    await wait_for_ready(model)


@log_calls_async
async def upgrade_snaps(model, channel):
    for app_name, blocking in {'kubernetes-master': True, 'kubernetes-worker': True, 'kubernetes-e2e': False}.items():
        app = model.applications.get(app_name)
        # missing applications are simply not upgraded
        if not app:
            continue

        config = await app.get_config()
        # If there is no change in the snaps skipping the upgrade
        if channel == config['channel']['value']:
            continue

        await app.set_config({'channel': channel})

        if blocking:
            for unit in app.units:
                # wait for blocked status
                deadline = time.time() + 180
                while time.time() < deadline:
                    if (unit.workload_status == 'blocked' and
                            unit.workload_status_message == 'Needs manual upgrade, run the upgrade action'):
                        break
                    await asyncio.sleep(3)
                else:
                    raise TimeoutError(
                        'Unable to find blocked status on unit {0} - {1} {2}'.format(
                            unit.name, unit.workload_status, unit.agent_status))

                # run upgrade action
                action = await unit.run_action('upgrade')
                await action.wait()
                assert action.status == 'completed'

    # wait for upgrade to complete
    await wait_for_ready(model)


async def retry_async_with_timeout(func, args, timeout_insec=600,
                                   timeout_msg="Timeout exceeded",
                                   retry_interval_insec=5):
    '''
    Retry a function until a timeout is exceeded. Function should
    return either True or Flase
    Args:
        func: The function to be retried
        args: Agruments of the function
        timeout_insec: What the timeout is (in seconds)
        timeout_msg: What to show in the timeout exception thrown
        retry_interval_insec: The interval between two consecutive executions

    '''
    deadline = time.time() + timeout_insec
    while time.time() < deadline:
        if await func(*args):
            break
        await asyncio.sleep(retry_interval_insec)
    else:
        raise TimeoutError(timeout_msg)


def arch():
    '''Return the package architecture as a string.'''
    architecture = check_output(['dpkg', '--print-architecture']).rstrip()
    architecture = architecture.decode('utf-8')
    return architecture
