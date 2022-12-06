#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Entrypoint to the `compose up` command.
"""

from meerschaum.utils.typing import SuccessTuple, Dict, Any, Optional, List

def compose_debug(
        action: Optional[List[str]] = None,
        debug: bool = False,
        **kw
    ) -> SuccessTuple:
    """
    Run a command from the isolated Meerschaum environment to debug issues.
    """
    from plugins.compose.utils import run_mrsm_command, init
    compose_config = init(debug=debug, **kw)

    run_mrsm_command(
        action or [],
        compose_config,
        capture_output = False,
        debug = debug,
    )

    return True, "Success"
