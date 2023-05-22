#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Entrypoint to the `compose down` command.
"""

from meerschaum.utils.warnings import info
from meerschaum.utils.typing import SuccessTuple, Dict, Any
from meerschaum.utils.misc import print_options
from meerschaum.utils.prompt import yes_no

def compose_down(
        debug: bool = False,
        drop: bool = False,
        yes: bool = False,
        force: bool = False,
        **kw
    ) -> SuccessTuple:
    """
    Bring up the configured Meerschaum stack.
    """
    from plugins.compose.utils import run_mrsm_command, init
    from plugins.compose.utils.pipes import (
        get_defined_pipes, build_custom_connectors,
        instance_pipes_from_pipes_list,
    )
    from plugins.compose.utils.stack import get_project_name
    compose_config = init(debug=debug, **kw)
    project_name = get_project_name(compose_config)
    run_mrsm_command(
        ['stop', 'jobs', '-f'],
        compose_config,
        capture_output = False,
        debug = debug,
    )

    if not drop:
        return True, "Success"

    custom_connectors = build_custom_connectors(compose_config)
    pipes = [pipe for pipe in get_defined_pipes(compose_config) if pipe.id is not None]
    if not pipes:
        return False, "No pipes to delete."
    instance_pipes = instance_pipes_from_pipes_list(pipes)

    print_options(pipes, header="Pipes to be deleted:")
    question = (
        f"Are you sure you want to delete {len(pipes)} pipe" + ('s' if len(pipes) != 1 else '')
        + (
            (
                " on 1 instance"
                if len(instance_pipes) == 1
                else f" across {len(instance_pipes)} instances"
            ) if len(pipes) > 1
            else ''
        )
        + "?"
    )

    if not yes_no(question, yes=yes, force=force, default='n'):
        return True, "Nothing was deleted."

    for instance_keys in instance_pipes:
        info(f"Deleting pipes tagged as '{project_name}' on instance '{instance_keys}'.")
        run_mrsm_command(
            ['delete', 'pipes', '-t', project_name, '-i', instance_keys, '-f'],
            compose_config,
            capture_output = False,
            debug = debug,
        )

    return True, "Success"
