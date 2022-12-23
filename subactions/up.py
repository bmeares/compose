#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Entrypoint to the `compose up` command.
"""

import meerschaum as mrsm
from meerschaum.utils.typing import SuccessTuple, Dict, Any, List
from meerschaum.utils.warnings import info, warn
from meerschaum.utils.misc import items_str, flatten_list, print_options

def compose_up(
        debug: bool = False,
        dry: bool = False,
        force: bool = False,
        **kw
    ) -> SuccessTuple:
    """
    Bring up the configured Meerschaum stack.
    """
    import shlex
    import copy
    from plugins.compose.utils import run_mrsm_command, init
    from plugins.compose.utils.stack import get_project_name
    from plugins.compose.utils.pipes import (
        build_custom_connectors, get_defined_pipes,
        instance_pipes_from_pipes_list,
    )
    from plugins.compose.utils.config import config_has_changed
    from collections import defaultdict

    compose_config = init(debug=debug, **kw)

    success, msg = check_and_install_plugins(compose_config, debug=debug)
    if not success:
        return success, msg

    ### Initialize the custom connectors and build the in-memory pipes.
    custom_connectors = build_custom_connectors(compose_config)
    pipes = get_defined_pipes(compose_config)
    instance_pipes = instance_pipes_from_pipes_list(pipes)

    ### Some useful parameters from the config file.
    project_name = get_project_name(compose_config)
    schedule = compose_config.get('sync', {}).get('schedule', None)
    min_seconds = compose_config.get('sync', {}).get('min_seconds', None)
    timeout_seconds = compose_config.get('sync', {}).get('timeout_seconds', None)
    args = compose_config.get('sync', {}).get('args', [])
    if isinstance(args, str):
        args = shlex.split(args)

    ### Update the parameters in case the remote has changed.
    updated_pipes = []
    updated_registration = False
    for pipe in pipes:
        updated_registration = False
        clean_pipe = mrsm.Pipe(**pipe.meta)
        if not pipe.id:
            pipe.register(debug=debug)
            updated_registration = True
        elif clean_pipe.parameters != pipe.parameters:
            ### Sometimes pipes can dynamically change parameters,
            ### so don't retrigger a verification in this case.
            pipe.edit(debug=debug)
            updated_registration = True

        if updated_registration:
            updated_pipes.append(pipe)

    ### Untag pipes that are tagged but no longer defined in mrsm-config.yaml.
    tagged_instance_pipes = {
        instance_keys: mrsm.get_pipes(
            tags = [project_name],
            instance = instance_keys,
            as_list = True,
            debug = debug,
        )
        for instance_keys in instance_pipes
    }
    for instance_connector, tagged_pipes in tagged_instance_pipes.items():
        for tagged_pipe in tagged_pipes:
            if tagged_pipe not in pipes:
                tagged_pipe.parameters.get('tags', [project_name]).remove(project_name)
                tagged_pipe.edit(debug=debug)

    if dry:
        return True, "Success"

    ### If any changes have been made to the config file's values,
    ### trigger another verification pass before starting jobs.
    if updated_registration and config_has_changed(compose_config):
        success, msg = verify_initial_syncs(updated_pipes, compose_config, debug=debug, **kw)
        if not success:
            return success, msg

    job_names = [project_name + f' sync ({instance_keys})' for instance_keys in instance_pipes]

    additional_args = copy.deepcopy(args)
    if schedule:
        if (
            '--schedule' not in args
            and
            '-s' not in args
            and
            '--cron' not in args
        ):
            additional_args += ['--schedule', schedule]
    elif '--loop' not in args:
        additional_args.append('--loop')

    if min_seconds is not None:
        if '--min-seconds' not in args and '--cooldown' not in args:
            additional_args += ['--min-seconds', str(min_seconds)]

    if timeout_seconds is not None:
        if '--timeout-seconds' not in args and '--timeout' not in args:
            additional_args += ['--timeout-seconds', str(timeout_seconds)]

    commands_to_run = [
        (
            [
                'sync', 'pipes', '-i', instance_keys, '-t', project_name,
                '--name', job_name, '-f', '-d',
            ]
            + additional_args
        )
        for instance_keys, job_name in zip(instance_pipes, job_names)
    ]

    for job_name, command in zip(job_names, commands_to_run):
        info(f"Starting job '{job_name}'...")
        run_mrsm_command(
            ['delete', 'job', job_name, '-f'],
            compose_config,
            capture_output = (not debug),
            debug = debug,
        )
        run_mrsm_command(command, compose_config, capture_output=False, debug=debug)

    if force:
        run_mrsm_command(
            ['show', 'logs'] + job_names,
            compose_config,
            capture_output = False,
            debug = debug,
        )

    if len(pipes) == 1:
        msg = f"Syncing {pipes[0]} in a background job."
    else:
        msg = (
            f"Syncing {len(pipes)} pipe" + ('s' if len(pipes) != 1 else '')
            + (" across " if len(job_names) != 1 else " on ")
            + f"{len(job_names)} instance" + ('s' if len(job_names) != 1 else '')
            + "."
            + ("\nRun `mrsm compose logs` or pass `-f` to follow logs output." if not force else '')
        )
    return True, msg


def check_and_install_plugins(compose_config: Dict[str, Any], debug: bool = False) -> SuccessTuple:
    """
    Verify that required plugins are available in the root directory
    and attempt to install missing plugins.
    """
    from meerschaum.config import get_config
    from plugins.compose.utils import run_mrsm_command
    required_plugins = compose_config.get('plugins', []) 
    default_repository = compose_config.get(
        'config',
        {}
    ).get(
        'meerschaum',
        {}
    ).get(
        'default_repository',
        get_config('meerschaum', 'default_repository')
    )
    existing_plugins = run_mrsm_command(
        ['show', 'plugins', '--nopretty'],
        compose_config,
        capture_output = True,
        debug = debug,
    ).communicate()[0].strip().decode("utf-8").split("\n")
    plugins_to_install = [
        plugin_name
        for plugin_name in required_plugins
        if plugin_name not in existing_plugins
    ]
    success = True
    if plugins_to_install:
        success = run_mrsm_command(
            (
                ['install', 'plugins']
                + plugins_to_install
                + (['-r', default_repository] if default_repository else [])
            ),
            compose_config,
            capture_output = False,
            debug = debug,
        ).wait() == 0
    msg = (
        "Success" if success
        else (
            "Unable to install plugins "
            + items_str(plugins_to_install)
            + f" from repository '{default_repository}'."
        )
    )
    return True, "Success"


def verify_initial_syncs(
        pipes: List[mrsm.Pipe],
        compose_config: Dict[str, Any],
        debug: bool = False,
        **kw: Any
    ) -> SuccessTuple:
    """
    Try two passes of syncing before starting the jobs.
    """
    from plugins.compose.utils import run_mrsm_command
    print_options(pipes, header=f"Verifying initial syncs for {len(pipes)} pipes:")

    failed_pipes = []
    for pipe in pipes:
        success = run_mrsm_command(
            [
                'sync', 'pipes', 
                '-c', pipe.connector_keys, '-m', pipe.metric_key, '-l', pipe.location_key,
                '-i', pipe.instance_keys,
            ],
            compose_config,
            capture_output = False,
            debug = debug,
        ).wait() == 0
        if not success:
            failed_pipes.append(pipe)

    if not failed_pipes:
        return True, "Success"

    ### Pipes may be interdependent, so try again if we encounter any errors.
    for pipe in failed_pipes:
        success = run_mrsm_command(
            [
                'sync', 'pipes', 
                '-c', pipe.connector_keys, '-m', pipe.metric_key, '-l', pipe.location_key,
                '-i', pipe.instance_keys,
            ],
            compose_config,
            capture_output = False,
            debug = debug,
        ).wait() == 0

        if not success:
            warn(f"Failed to sync {pipe}!", stack=False)
            return False, f"Unable to begin syncing {pipe}."
    return True, "Success"
