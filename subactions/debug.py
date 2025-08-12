#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Entrypoint to the `compose up` command.
"""

from meerschaum.utils.typing import SuccessTuple, Any, Optional, List, Dict
from meerschaum.plugins import from_plugin_import


def _compose_debug(
    compose_config: Dict[str, Any],
    action: Optional[List[str]] = None,
    debug: bool = False,
    **kw: Any
) -> SuccessTuple:
    """
    Run a command from the isolated Meerschaum environment to debug issues.
    """
    run_mrsm_command = from_plugin_import('compose.utils', 'run_mrsm_command')

    run_mrsm_command(
        action or [],
        compose_config,
        capture_output=False,
        debug=debug,
        _replace=False,
    )

    return True, "Success"
