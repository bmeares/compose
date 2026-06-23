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

    ### Always run passthrough commands in a SUBPROCESS. In-process execution cannot
    ### reliably redirect Meerschaum's import-time path resolution (notably the venvs
    ### dir): re-pointing the root mid-process does not move where `install required` /
    ### `setup plugins` write, so they land in the HOST's `~/.config/meerschaum/venvs`
    ### instead of the project's `root/venvs` (the package installs, but the project
    ### venvs stay empty). A fresh subprocess reads the compose env (absolute
    ### MRSM_ROOT_DIR) at import, so paths/venvs resolve under the project root — this is
    ### also how `compose init` already installs deps correctly.
    _subprocess = True
    if action:
        info(f"Running '{' '.join(action)}' in compose project '{project_name}'...")

    success, msg = run_mrsm_command(
        isolated_sysargs,
        compose_config,
        debug=debug,
        _subprocess=_subprocess,
        _replace=False,
    )
    return success, msg
