#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Entrypoint to `mrsm compose init`.
"""

from meerschaum.utils.typing import SuccessTuple, Dict, Any
from meerschaum.utils.warnings import info, warn
from meerschaum.utils.misc import items_str

def compose_init(
        debug: bool = False,
        **kw: Any
    ) -> SuccessTuple:
    """
    Install the required dependencies for this compose project.
    This is useful for building Docker images.
    """
    from plugins.compose.utils import run_mrsm_command, init
    from plugins.compose.utils.plugins import (
        check_and_install_plugins,
        get_installed_plugins,
    )
    from plugins.compose.utils.stack import get_project_name
    compose_config = init(debug=debug, **kw)
    project_name = get_project_name(compose_config)
    existing_plugins = get_installed_plugins(compose_config, debug=debug)
    plugins_success, plugins_msg = check_and_install_plugins(
        compose_config,
        debug = debug,
        _existing_plugins = existing_plugins,
    )
    if not plugins_success:
        return plugins_success, plugins_msg

    if existing_plugins:
        install_required_success = (
            run_mrsm_command(
                ['install', 'required'] + existing_plugins,
                compose_config,
                capture_output = False,
                debug = debug,
            ).wait() == 0
        )
        if not install_required_success:
            return False, f"Failed to install required packages for project '{project_name}'."

        setup_success = (
            run_mrsm_command(
                ['setup', 'plugins'],
                compose_config,
                capture_output = False,
                debug = debug,
            ).wait() == 0
        )
        if not setup_success:
            return False, f"Failed to setup plugins for project '{project_name}'."

    return True, f"Finished initializing project '{project_name}'."
