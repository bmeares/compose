#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Show the jobs' states.
"""

from meerschaum.utils.typing import SuccessTuple, Dict, Any, Optional, List

def compose_ps(
        action: Optional[List[str]] = None,
        sysargs: Optional[List[str]] = None,
        nopretty: bool = False,
        debug: bool = False,
        **kw,
    ) -> SuccessTuple:
    """
    Execute Meerschaum actions in the isolated environment.
    """
    from plugins.compose.utils import run_mrsm_command, init
    compose_config = init(debug=debug, **kw)

    success = run_mrsm_command(
        ['show', 'jobs'] + (['--nopretty'] if nopretty else []),
        compose_config,
        capture_output = False,
        debug = debug,
    ).wait() == 0
    msg = "Success" if success else f"Failed to execute '{' '.join(action)}'."

    return success, msg
