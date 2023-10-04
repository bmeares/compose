#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Manage plugins in the isolated environment.
"""

from collections import defaultdict
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
    from meerschaum.config.static import STATIC_CONFIG
    from plugins.compose.utils import run_mrsm_command
    configured_plugins = compose_config.get('plugins', []) 
    if not configured_plugins:
        return True, "Success"

    if not isinstance(configured_plugins, list):
        return False, "Required plugins must be a list."

    default_repository = compose_config.get(
        'config', {}
    ).get(
        'meerschaum', {}
    ).get(
        'default_repository', get_config('meerschaum', 'default_repository')
    )

    required_plugin_parts = [
        plugin_name.split(STATIC_CONFIG['plugins']['repo_separator'])
        for plugin_name in configured_plugins
    ]
    required_plugins = defaultdict(lambda: [])
    for plugin_parts in required_plugin_parts:
        plugin_name = plugin_parts[0]
        repo_keys = (
            plugin_parts[1]
            if len(plugin_parts) > 1
            else default_repository
        )
        required_plugins[repo_keys].append(plugin_name)

    existing_plugins = _existing_plugins or get_installed_plugins(compose_config)
    plugins_to_install = [
        plugin_parts[0]
        for plugin_parts in required_plugin_parts
        if plugin_parts[0] not in existing_plugins
    ]
    if not plugins_to_install:
        return True, "Required plugins are already installed."

    success, msg = True, ""
    for repo_keys, plugin_names in required_plugins.items():
        install_success = run_mrsm_command(
            (
                ['install', 'plugins']
                + plugin_names
                + (['-r', repo_keys] if repo_keys else [])
            ),
            compose_config,
            capture_output = False,
            debug = debug,
        ).wait() == 0
        install_msg = (
            ""
            if install_success
            else (
                f"Failed to install plugins {items_str(plugin_names)} "
                + f"from repository {repo_keys or default_repository}.\n"
            )
        )
        if not install_success:
            warn(install_msg, stack=False)
        success = success and install_success
        msg += install_msg

    msg = "Success" if success else msg
    return success, msg.rstrip()
