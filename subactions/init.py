#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Entrypoint to `mrsm compose init`.
"""

import os
import pathlib
from meerschaum.utils.typing import SuccessTuple, Any, Optional
from meerschaum.utils.warnings import info


def _compose_init(
    _,
    debug: bool = False,
    file: Optional[pathlib.Path] = None,
    yes: bool = False,
    force: bool = False,
    **kw: Any
) -> SuccessTuple:
    """
    Install the required dependencies for this compose project.
    This is useful for building Docker images.
    """
    from plugins.compose.utils import run_mrsm_command, init as _init
    from plugins.compose.utils.config import infer_compose_file_path
    from plugins.compose.utils.plugins import (
        check_and_install_plugins,
        get_installed_plugins,
    )
    from plugins.compose.utils.stack import get_project_name
    from meerschaum.utils.prompt import yes_no

    compose_path = infer_compose_file_path(file)
    if compose_path is None:
        cwd_path = pathlib.Path(os.getcwd())
        compose_path = cwd_path / 'mrsm-compose.yaml'
        file = compose_path
        info("No compose project could be found.")
        try:
            create_new_compose_file = yes_no(
                f"Create new project '{cwd_path.name}'?\n    ({compose_path})",
                yes = yes,
                force = force,
            )
        except (Exception, KeyboardInterrupt):
            create_new_compose_file = False

        if not create_new_compose_file:
            return False, "No files were created."

        if not _write_new_compose_file(compose_path):
            return False, f"Failed to create file '{compose_path}'."

    compose_config = _init(file=file, debug=debug, **kw)
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


def _write_new_compose_file(compose_path: pathlib.Path) -> bool:
    """
    Write these the following text to a new project's compose file.
    """
    from meerschaum.config._edit import general_write_yaml_config

    if compose_path.exists():
        raise FileExistsError(f"File '{compose_path}' already exists.")

    return general_write_yaml_config({
        compose_path: (
            {
                'project_name': compose_path.parent.name,
                'root_dir': './root',
                'plugins_dir': ['./plugins'],
                'pipes': [],
                'plugins': [],
                'config': {
                    'meerschaum': {
                        'connectors': {
                            'sql': {
                                'main': 'MRSM{meerschaum:connectors:sql:main}',
                            },
                        },
                    },
                },
                'environment': {},
            },
            "### See https://meerschaum.io/reference/compose/ for the compose schema.\n\n",
        )
    })
