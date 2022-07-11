#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Entrypoint to the `compose up` command.
"""

from meerschaum.utils.typing import SuccessTuple, Dict, Any

def compose_up(
        compose_config: Dict[str, Any],
        debug: bool = False,
        **kw
    ) -> SuccessTuple:
    """
    Bring up the configured Meerschaum stack.
    """
    from plugins.compose.utils import run_mrsm_command
    if debug:
        run_mrsm_command(
            ['show', 'config', 'stack'],
            compose_config,
            capture_output = False,
            debug = debug,
        )

    run_mrsm_command(
        ['stack', 'up', '-d', 'db'],
        compose_config,
        capture_output = False,
        debug = debug,
    )

    return True, "Success"
