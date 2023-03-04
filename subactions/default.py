#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Pass all other subactions to `mrsm stack`.
"""

from meerschaum.utils.typing import SuccessTuple, Dict, Any, Optional, List
from meerschaum.utils.warnings import info

def compose_default(
        action: Optional[List[str]] = None,
        sysargs: Optional[List[str]] = None,
        debug: bool = False,
        **kw,
    ) -> SuccessTuple:
    """
    Execute Meerschaum actions in the isolated environment.
    """
    from plugins.compose.utils import run_mrsm_command, init
    from plugins.compose.utils.stack import get_project_name
    compose_config = init(debug=debug, **kw)
    project_name = get_project_name(compose_config)

    isolated_sysargs = []
    found_file = False
    for arg in sysargs[1:]:
        if arg in ('--file', '--env-file'):
            found_file = True
            continue
        if found_file:
            found_file = False
            continue
        isolated_sysargs.append(arg)

    info(f"Running '{' '.join(action)}' in compose project '{project_name}'...")
    success = run_mrsm_command(
        isolated_sysargs,
        compose_config,
        capture_output = False,
        debug = debug,
    ).wait() == 0
    msg = "Success" if success else f"Failed to execute '{' '.join(action)}'."

    return success, msg
