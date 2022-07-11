#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2022 bmeares <bmeares@fedora>
#
# Distributed under terms of the MIT license.

"""
Entrypoint to the `compose down` command.
"""

from meerschaum.utils.typing import SuccessTuple, Dict, Any

def compose_down(
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
        ['stack', 'down'],
        compose_config,
        capture_output = False,
        debug = debug,
    )

    return True, "Success"
