#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Manage plugins in the isolated environment.
"""

from meerschaum.utils.typing import Dict, Any, List, SuccessTuple, Optional
from meerschaum.utils.packages import run_python_package
from meerschaum.utils.warnings import info, warn
from meerschaum.utils.misc import items_str

def get_installed_plugins(
        compose_config: Dict[str, Any],
        debug: bool = False,
    ) -> List[str]:
    """
    Return a list of plugins in the `root/plugins/` directory.
    """
    from plugins.compose.utils import run_mrsm_command
    proc = run_mrsm_command(
        ['show', 'plugins', '--nopretty'], compose_config, debug=debug,
    )
    return [line.decode('utf-8').strip('\n') for line in proc.stdout.readlines()]


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


def check_and_install_plugins(
        compose_config: Dict[str, Any],
        debug: bool = False,
        _existing_plugins: Optional[List[str]] = None,
    ) -> SuccessTuple:
    """
    Verify that required plugins are available in the root directory
    and attempt to install missing plugins.
    """
    from meerschaum.config import get_config
    from plugins.compose.utils import run_mrsm_command
    required_plugins = compose_config.get('plugins', []) 
    default_repository = compose_config.get(
        'config',
        {}
    ).get(
        'meerschaum',
        {}
    ).get(
        'default_repository',
        get_config('meerschaum', 'default_repository')
    )
    existing_plugins = _existing_plugins or get_installed_plugins(compose_config)
    plugins_to_install = [
        plugin_name
        for plugin_name in required_plugins
        if plugin_name not in existing_plugins
    ]
    success = True
    if plugins_to_install:
        success = run_mrsm_command(
            (
                ['install', 'plugins']
                + plugins_to_install
                + (['-r', default_repository] if default_repository else [])
            ),
            compose_config,
            capture_output = False,
            debug = debug,
        ).wait() == 0
    msg = (
        "Success" if success
        else (
            "Unable to install plugins "
            + items_str(plugins_to_install)
            + f" from repository '{default_repository}'."
        )
    )
    return True, "Success"
