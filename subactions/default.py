#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Pass all other subactions to `mrsm`.
"""

from meerschaum.utils.typing import SuccessTuple, Any, Optional, List, Dict
from meerschaum.utils.warnings import info
from meerschaum.plugins import from_plugin_import


def _compose_default(
    compose_config: Dict[str, Any],
    action: Optional[List[str]] = None,
    sysargs: Optional[List[str]] = None,
    debug: bool = False,
    **kw: Any,
) -> SuccessTuple:
    """
    Execute Meerschaum actions in the isolated environment.
    """
    try:
        run_mrsm_command = from_plugin_import('compose.utils', 'run_mrsm_command')
    except ImportError:
        return (
            False,
            (
                f"Failed to execute `{' '.join(action or [])}`."
                + "\nRun `mrsm compose init` before proceeding."
            )
        )

    get_project_name = from_plugin_import('compose.utils.stack', 'get_project_name')

    project_name = get_project_name(compose_config)

    isolated_sysargs = []
    found_file = False
    if sysargs:
        for arg in sysargs[1:]:
            if arg in ('--file', '--env-file'):
                found_file = True
                continue
            if found_file:
                found_file = False
                continue
            isolated_sysargs.append(arg)

    ### Just launch a subprocess for the shell.
    ### It's too much of a hassle otherwise.
    _subprocess = compose_config.get('isolation', None) == 'subprocess'
    if action:
        info(f"Running '{' '.join(action)}' in compose project '{project_name}'...")
    else:
        _subprocess = True

    success, msg = run_mrsm_command(
        isolated_sysargs,
        compose_config,
        debug=debug,
        _subprocess=_subprocess,
        _replace=False,
    )
    return success, msg
