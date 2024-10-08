#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Entrypoint to the `compose up` command.
"""

from meerschaum.utils.typing import SuccessTuple, Any, Optional, List
from meerschaum.plugins import from_plugin_import

def compose_debug(
    action: Optional[List[str]] = None,
    debug: bool = False,
    **kw: Any
) -> SuccessTuple:
    """
    Run a command from the isolated Meerschaum environment to debug issues.
    """
    run_mrsm_command, init = from_plugin_import('compose.utils', 'run_mrsm_command', 'init')
    compose_config = init(debug=debug, **kw)

    run_mrsm_command(
        action or [],
        compose_config,
        capture_output=False,
        debug=debug,
    )

    return True, "Success"
