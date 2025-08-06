#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Pass all other subactions to `mrsm`.
"""

from meerschaum.utils.typing import SuccessTuple, Any, Optional, List, Dict
from meerschaum.utils.warnings import info


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
    from meerschaum.plugins import from_plugin_import
    run_mrsm_command = from_plugin_import('compose.utils', 'run_mrsm_command')
    print('GET PROJECT NAME')
    get_project_name = from_plugin_import('compose.utils.stack', 'get_project_name')
    print(f"{get_project_name=}")

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

    info(f"Running '{' '.join(action)}' in compose project '{project_name}'...")
    success = run_mrsm_command(
        isolated_sysargs,
        compose_config,
        capture_output=False,
        debug=debug,
    ).wait() == 0
    msg = "Success" if success else f"Failed to execute '{' '.join(action)}'."

    return success, msg
