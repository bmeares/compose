#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Entrypoint to the `compose up` command.
"""

import json

import meerschaum as mrsm
from meerschaum.utils.typing import SuccessTuple, Dict, Any, List, Optional
from meerschaum.utils.warnings import info, warn
from meerschaum.utils.misc import print_options


def _compose_up(
    compose_config: Dict[str, Any],
    dry: bool = False,
    force: bool = False,
    presync: bool = False,
    no_jobs: bool = False,
    sysargs: Optional[List[str]] = None,
    debug: bool = False,
    **kw
) -> SuccessTuple:
    """
    Bring up the configured Meerschaum stack.
    """
    from meerschaum.plugins import from_plugin_import

    run_mrsm_command = from_plugin_import('compose.utils', 'run_mrsm_command')
    get_project_name = from_plugin_import('compose.utils.stack', 'get_project_name')
    check_and_install_plugins = from_plugin_import('compose.utils.plugins', 'check_and_install_plugins')
    build_custom_connectors, get_defined_pipes, instance_pipes_from_pipes_list = from_plugin_import(
        'compose.utils.pipes',
        'build_custom_connectors',
        'get_defined_pipes',
        'instance_pipes_from_pipes_list',
    )
    get_jobs_commands = from_plugin_import('compose.utils.jobs', 'get_jobs_commands')
    config_has_changed = from_plugin_import('compose.utils.config', 'config_has_changed')
    no_daemon_flags = (
        ['--no-daemon']
        if compose_config.get('isolation', None) == 'subprocess'
        else []
    )

    success, msg = check_and_install_plugins(compose_config, debug=debug)
    if not success:
        return success, msg

    ### Initialize the custom connectors and build the in-memory pipes.
    custom_connectors = build_custom_connectors(compose_config)
    pipes = get_defined_pipes(compose_config)
    instance_pipes = instance_pipes_from_pipes_list(pipes)
    project_name = get_project_name(compose_config)

    ### Update the parameters in case the remote has changed.
    updated_pipes = []
    updated_registration = False
    for pipe in pipes:
        updated_registration = False
        clean_pipe = mrsm.Pipe(**pipe.meta)
        remote_parameters = clean_pipe.parameters
        local_parameters = pipe._attributes['parameters']

        local_parameters_str = json.dumps(local_parameters, sort_keys=True)
        remote_parameters_str = json.dumps(remote_parameters, sort_keys=True)

        if pipe.temporary:
            info(f"{pipe} is temporary, will not modify registration.")
        elif not pipe.id:
            info(f"Registering {pipe}...")
            success, msg = run_mrsm_command(
                [
                    'register', 'pipes',
                    '-c', str(pipe.connector_keys),
                    '-m', str(pipe.metric_key),
                    '-l', str(pipe.location_key),
                    '-i', str(pipe.instance_keys),
                    '--params', json.dumps(pipe.parameters),
                    '--noask',
                ] + no_daemon_flags,
                compose_config,
                capture_output=False,
                debug=debug,
                _replace=False,
            )
            if not success:
                warn(f"Failed to register {pipe}.", stack=False)
            updated_registration = True

        ### Check the remote parameters against the specified parameters in the YAML.
        elif local_parameters_str != remote_parameters_str:
            ### Editing with `--params` in a subprocess only patches,
            ### so instead replace the parameters dictionary directly.
            info(f"Updating parameters for {pipe}...")
            success, msg = pipe.edit(debug=debug)
            if not success:
                warn(f"Failed to edit {pipe}.", stack=False)
            updated_registration = True

        if updated_registration or presync or pipe.temporary:
            updated_pipes.append(pipe)

    ### Untag pipes that are tagged but no longer defined in mrsm-config.yaml.
    from meerschaum.connectors import connectors
    tagged_instance_pipes = {
        instance_keys: mrsm.get_pipes(
            tags=[project_name],
            instance=custom_connectors.get(instance_keys, instance_keys),
            as_list=True,
            debug=debug,
        )
        for instance_keys in instance_pipes
    }
    for instance_connector, tagged_pipes in tagged_instance_pipes.items():
        for tagged_pipe in tagged_pipes:
            if tagged_pipe not in pipes:
                try:
                    tagged_pipe.tags = [
                        _tag
                        for _tag in tagged_pipe.tags
                        if _tag != project_name
                    ]
                except Exception:
                    warn(f"{tagged_pipe} was incorrectly tagged with '{project_name}'...")
                    continue
                info(f"Removing tag '{project_name}' from {tagged_pipe}...")
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
    if presync or (updated_pipes and config_has_changed(compose_config)):
        ran_verification_sync = True
        print_options(
            pipes,
            header = (
                f"Running initial syncs for {len(updated_pipes)} pipe"
                + ('s' if len(updated_pipes) != 1 else '')
                + ':'
            ),
        )
        success, msg = run_initial_syncs(
            updated_pipes,
            compose_config,
            sysargs,
            debug = debug,
            **kw
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
                else "Nothing to do."
            )
        )
        return True, msg

    jobs_commands = get_jobs_commands(compose_config)
    for job_name, job_command in jobs_commands.items():
        info(f"Starting job '{job_name}'...")
        run_mrsm_command(
            ['delete', 'job', job_name, '-f'],
            compose_config,
            capture_output=(not debug),
            debug=debug,
            _replace=False,
        )
        run_mrsm_command(
            job_command,
            compose_config,
            capture_output=False,
            debug=debug,
            _replace=False,
        )

    if force:
        run_mrsm_command(
            ['show', 'logs'] + list(jobs_commands),
            compose_config,
            capture_output=False,
            debug=debug,
            _replace=False,
        )

    explicit_jobs = compose_config.get('jobs', {})
    if explicit_jobs:
        msg = (
            f"Running {len(jobs_commands)} background job"
            + ('s' if len(jobs_commands) != 1 else '')
            + '.'
        )
    elif len(pipes) == 1:
        msg = f"Syncing {pipes[0]} in a background job."
    else:
        msg = (
            f"Syncing {len(pipes)} pipe" + ('s' if len(pipes) != 1 else '')
            + (" across " if len(jobs_commands) != 1 else " on ")
            + f"{len(jobs_commands)} instance"
            + ('s' if len(jobs_commands) != 1 else '')
            + "."
        )

    msg += (
        "\nRun `mrsm compose logs` or pass `-f` to follow logs output."
        if not force
        else ''
    )
    return True, msg


def run_initial_syncs(
    pipes: List[mrsm.Pipe],
    compose_config: Dict[str, Any],
    sysargs: Optional[List[str]] = None,
    debug: bool = False,
    **kw
) -> SuccessTuple:
    """
    Try two passes of syncing before starting the jobs.
    """
    from meerschaum.plugins import from_plugin_import
    run_mrsm_command = from_plugin_import('compose.utils', 'run_mrsm_command')
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
            and (i - 1) not in indices_to_remove
    ]
    if '--no-daemon' not in flags:
        flags.append('--no-daemon')

    failed_pipes = []
    for pipe in pipes:
        info(f"Syncing {pipe}...")
        success, msg = (
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
                capture_output=False,
                debug=debug,
                _replace=False,
            )
            if not pipe.temporary
            else pipe.sync(debug=debug, **kw)
        )

        if not success:
            warn(f"Failed to sync {pipe}:\n{msg}", stack=False)
            failed_pipes.append(pipe)

    if not failed_pipes:
        return True, "Success"

    ### Pipes may be interdependent, so try again if we encounter any errors.
    for pipe in failed_pipes:
        info(f"Retry syncing {pipe}...")
        success, msg = (
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
                capture_output=False,
                debug=debug,
                _replace=False,
            )
            if not pipe.temporary
            else pipe.sync(debug=debug, **kw)[0]
        )

        if not success:
            warn(f"Failed to sync {pipe}:\n{msg}", stack=False)
            return False, f"Unable to begin syncing {pipe}:\n{msg}"

    return True, "Success"
