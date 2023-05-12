#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Entrypoint to the `compose up` command.
"""

import meerschaum as mrsm
from meerschaum.utils.typing import SuccessTuple, Dict, Any, List, Optional
from meerschaum.utils.warnings import info, warn
from meerschaum.utils.misc import items_str, flatten_list, print_options

def compose_up(
        debug: bool = False,
        dry: bool = False,
        force: bool = False,
        verify: bool = False,
        no_jobs: bool = False,
        sysargs: Optional[List[str]] = None,
        **kw
    ) -> SuccessTuple:
    """
    Bring up the configured Meerschaum stack.
    """
    import shlex
    import copy
    import json
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
        if pipe.temporary:
            info(f"{pipe} is temporary, will not modify registration.")
        elif not pipe.id:
            info(f"Registering {pipe}...")
            success = run_mrsm_command(
                [
                    'register', 'pipes', 
                    '-c', str(pipe.connector_keys),
                    '-m', str(pipe.metric_key),
                    '-l', str(pipe.location_key),
                    '-i', str(pipe.instance_keys),
                    '--params', json.dumps(pipe.parameters),
                    '--noask',
                ],
                compose_config,
                capture_output = True,
                debug = debug,
            ).wait() == 0
            if not success:
                warn(f"Failed to register {pipe}.", stack=False)
            updated_registration = True

        ### Check the remote parameters against the specified parameters in the YAML.
        elif clean_pipe.parameters != pipe._attributes['parameters']:
            ### Editing with `--params` in a subprocess only patches,
            ### so instead replace the parameters dictionary directly.
            info(f"Updating parameters for {pipe}...")
            success, msg = pipe.edit(debug=debug)
            if not success:
                warn(f"Failed to edit {pipe}.", stack=False)
            updated_registration = True

        if updated_registration or verify or pipe.temporary:
            updated_pipes.append(pipe)

    ### Untag pipes that are tagged but no longer defined in mrsm-config.yaml.
    from meerschaum.connectors import connectors
    tagged_instance_pipes = {
        instance_keys: mrsm.get_pipes(
            tags = [project_name],
            instance = custom_connectors.get(instance_keys, instance_keys),
            as_list = True,
            debug = debug,
        )
        for instance_keys in instance_pipes
    }
    for instance_connector, tagged_pipes in tagged_instance_pipes.items():
        for tagged_pipe in tagged_pipes:
            if tagged_pipe not in pipes:
                info(f"Removing tag '{project_name}' from {tagged_pipe}...")
                tagged_pipe.parameters.get('tags', [project_name]).remove(project_name)
                tagged_pipe.edit(debug=debug)

    if dry:
        return True, (
            f"Updated parameters for {len(pipes)} pipe"
            + ("s" if len(pipes) != 1 else "")
            + (" across " if len(instance_pipes) != 1 else " on ")
            + f"{len(instance_pipes)} instance"
            + ("s" if len(instance_pipes) != 1 else "")
            + "."
        )

    ### If any changes have been made to the config file's values,
    ### trigger another verification pass before starting jobs.
    ran_verification_sync = False
    if verify or (updated_pipes and config_has_changed(compose_config)):
        ran_verification_sync = True
        print_options(pipes, header=f"Verifying initial syncs for {len(updated_pipes)} pipes:")
        success, msg = verify_initial_syncs(
            updated_pipes,
            compose_config,
            sysargs,
            debug = debug,
        )
        if not success:
            return success, msg

    if no_jobs:
        msg = (
            (
                f"Synced {len(updated_pipes)} pipe"
                + ("s" if len(updated_pipes) != 1 else "")
                + f" across {len(instance_pipes)} instance"
                + ("s" if len(instance_pipes) != 1 else "")
                + "."
            )
            if ran_verification_sync
            else (
                (
                    f"Updated {len(updated_pipes)} pipe"
                    + ("s" if len(updated_pipes) != 1 else "")
                    + f" across {len(instance_pipes)} instance"
                    + "."
                )
                if updated_pipes
                else f"Nothing to do."
            )
        )
        return True, msg

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
        sysargs: Optional[List[str]] = None,
        debug: bool = False,
    ) -> SuccessTuple:
    """
    Try two passes of syncing before starting the jobs.
    """
    import json
    from plugins.compose.utils import run_mrsm_command
    from meerschaum._internal.arguments._parse_arguments import parse_dict_to_sysargs

    flags_to_remove = {
        '-c', '-C', '--connector-keys',
        '-m', '-M', '--metric-keys',
        '-l', '-L', '--location-keys',
        '-i', '-I', '--mrsm-instance', '--instance',
    }
    sysargs = sysargs or []
    indices_to_remove = {i for i, flag in enumerate(sysargs) if flag in flags_to_remove}
    flags = [
        flag
        for i, flag in enumerate(sysargs)
        if i not in indices_to_remove
            or (i - 1) not in indices_to_remove
    ]

    failed_pipes = []
    for pipe in pipes:
        info(f"Syncing {pipe}...")
        success = (
            run_mrsm_command(
                [
                    'sync',
                    'pipes', 
                    '-c', str(pipe.connector_keys),
                    '-m', str(pipe.metric_key),
                    '-l', str(pipe.location_key),
                    '-i', str(pipe.instance_keys),
                ] + flags,
                compose_config,
                capture_output = False,
                debug = debug,
            ).wait() == 0
            if not pipe.temporary
            else pipe.sync(debug=debug, **kw)[0]
        )

        if not success:
            warn(f"Failed to sync {pipe}.", stack=False)
            failed_pipes.append(pipe)

    if not failed_pipes:
        return True, "Success"

    ### Pipes may be interdependent, so try again if we encounter any errors.
    for pipe in failed_pipes:
        info(f"Retry syncing {pipe}...")
        success = (
            run_mrsm_command(
                [
                    'sync',
                    'pipes', 
                    '-c', str(pipe.connector_keys),
                    '-m', str(pipe.metric_key),
                    '-l', str(pipe.location_key),
                    '-i', str(pipe.instance_keys),
                ] + flags,
                compose_config,
                capture_output = False,
                debug = debug,
            ).wait() == 0
            if not pipe.temporary
            else pipe.sync(debug=debug, **kw)[0]
        )

        if not success:
            warn(f"Failed to sync {pipe}!", stack=False)
            return False, f"Unable to begin syncing {pipe}."
    return True, "Success"
