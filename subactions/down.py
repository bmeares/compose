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
        debug: bool = False,
        **kw
    ) -> SuccessTuple:
    """
    Bring up the configured Meerschaum stack.
    """
    from plugins.compose.utils import run_mrsm_command, init
    compose_config = init(debug=debug, **kw)
    if debug:
        run_mrsm_command(
            ['show', 'config', 'stack'],
            compose_config,
            capture_output = False,
            debug = debug,
        )

    run_mrsm_command(
        ['stop', 'jobs', '-f'],
        compose_config,
        capture_output = False,
        debug = debug,
    )

    return True, "Success"
