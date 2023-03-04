#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Utility functions for the `stack` command.
"""

import os
import pathlib
from meerschaum.utils.typing import Dict, Any
from meerschaum.utils.warnings import warn
from meerschaum.utils.daemon._names import generate_random_name

def get_project_name(compose_config: Dict[str, Any]) -> str:
    """
    Determine the `docker-compose` project name.
    """
    root_project_name = compose_config.get('project_name', None)
    stack_project_name = compose_config.get('stack', {}).get('project_name', None)
    default_project_name = compose_config['__file__'].parent.stem

    if root_project_name:
        project_name = root_project_name
    elif stack_project_name:
        project_name = stack_project_name
        warn(
            f"Detected a project_name '{stack_project_name}' under 'config:stack:project_name'.\n"
            + "    Will use this as the project name for this compose file.",
            stack = False,
        )
    else:
        project_name = default_project_name

    return project_name


def ensure_project_name(compose_config: Dict[str, Any]) -> None:
    """
    Ensure the project name is set in the compose configuration dictionary.
    """
    project_name = get_project_name(compose_config)
    compose_config['project_name'] = project_name
    if 'config' not in compose_config:
        compose_config['config'] = {}
    if 'stack' not in compose_config['config']:
        compose_config['config']['stack'] = {}
    compose_config['config']['stack']['project_name'] = project_name
