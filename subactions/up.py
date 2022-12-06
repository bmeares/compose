#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Entrypoint to the `compose up` command.
"""

import meerschaum as mrsm
from meerschaum.utils.typing import SuccessTuple, Dict, Any, List
from meerschaum.utils.warnings import info, warn
from meerschaum.utils.misc import items_str, flatten_list

def compose_up(
        debug: bool = False,
        **kw
    ) -> SuccessTuple:
    """
    Bring up the configured Meerschaum stack.
    """
    import copy
    from meerschaum.config import get_config
    from plugins.compose.utils import run_mrsm_command, init
    from plugins.compose.utils.stack import get_project_name
    from collections import defaultdict

    compose_config = init(debug=debug, **kw)

    success, msg = check_and_install_plugins(compose_config, debug=debug)
    if not success:
        return success, msg

    project_name = get_project_name(compose_config)
    default_instance = compose_config.get(
        'config',
        {}
    ).get(
        'meerschaum',
        {}
    ).get(
        'instance',
        get_config('meerschaum', 'instance')
    )
    sync_pipes_meta = compose_config.get('sync', {}).get('pipes', [])
    schedule = compose_config.get('sync', {}).get('schedule', None)
    
    custom_connectors_config = compose_config.get(
        'config',
        {}
    ).get(
        'meerschaum',
        {}
    ).get(
        'connectors',
        {}
    )
    custom_connectors = {}
    for typ, labels in custom_connectors_config.items():
        for label, connector_kwargs in labels.items():
            conn_keys = typ + ':' + label
            custom_connectors[conn_keys] = mrsm.get_connector(conn_keys, **connector_kwargs)

    instance_pipes = defaultdict(lambda: [])
    for _pipe_meta in sync_pipes_meta:
        pipe_meta = copy.deepcopy(_pipe_meta)
        if 'tags' not in pipe_meta:
            pipe_meta['tags'] = []
        pipe_meta['tags'].append(project_name)
        if 'instance' not in pipe_meta and 'mrsm_instance' not in pipe_meta:
            pipe_meta['instance'] = default_instance
        pipe = mrsm.Pipe(**pipe_meta)
        clean_pipe = mrsm.Pipe(
            pipe.connector_keys, pipe.metric_key, pipe.location_key,
            instance=pipe.instance_connector,
        )
        instance_pipes[str(pipe.instance_connector)].append(pipe)
        if not pipe.id:
            pipe.register(debug=debug)
        elif clean_pipe.parameters != pipe.parameters:
            pipe.edit(debug=debug)

    pipes = list(flatten_list([pipe for pipe in instance_pipes.values()]))
    success, msg = verify_initial_syncs(pipes, compose_config, debug=debug, **kw)
    if not success:
        return success, msg

    job_names = [project_name + f' sync ({instance_keys})' for instance_keys in instance_pipes]
    commands_to_run = [
        (
            [
                'start', 'job',
                'sync', 'pipes', '-i', instance_keys, '-t', project_name,
                '--name', job_name, '-f',
            ]
            + (['--schedule', schedule] if schedule else ['--loop'])
        )
        for instance_keys, job_name in zip(instance_pipes, job_names)
    ]

    for job_name, command in zip(job_names, commands_to_run):
        run_mrsm_command(['delete', 'job', job_name, '-f'], compose_config, capture_output=(not debug), debug=debug)
        run_mrsm_command(command, compose_config, capture_output=False, debug=debug)

    run_mrsm_command(
        ['show', 'logs'] + job_names,
        compose_config,
        capture_output = False,
        debug = debug,
    )

    return True, "Success"


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
    info("Verifying the initial syncs for " + items_str(pipes, quotes=False) + '.')

    ### Pipes may be interdependent, so ignore first success status.
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
            warn(f"Failed to sync {pipe}!", stack=False)
            return False, f"Unable to begin syncing {pipe}."
    return True, "Success"
