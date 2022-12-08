#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Manage plugins in the isolated environment.
"""

from meerschaum.utils.typing import Dict, Any, List
from meerschaum.utils.packages import run_python_package

def get_installed_plugins(
        compose_config: Dict[str, Any],
        debug: bool = False,
    ):
    """
    Return a list of plugins in the `root/plugins/` directory.
    """
    from plugins.compose.utils import run_mrsm_command
    proc = run_mrsm_command(
        ['show', 'plugins', '--nopretty'], compose_config, debug=debug,
    )
    return [line.decode('utf-8') for line in proc.stdout.readlines()]


def install_plugins(
        plugins: List[str],
        compose_config: Dict[str, Any],
        debug: bool = False,
    ) -> bool:
    """
    Install plugins to the `root/plugins/` directory.
    """
    from plugins.compose.utils import run_mrsm_command
    return run_mrsm_command(
        ['install', 'plugins'] + plugins, compose_config, debug=debug,
    ).wait() == 0
