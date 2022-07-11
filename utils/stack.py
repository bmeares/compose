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
    project_name = compose_config.get('stack', {}).get(
        'project_name', pathlib.Path(os.getcwd()).stem
    )
    if project_name == 'mrsm':
        raise Exception(
            "Your stack project name cannot be 'mrsm'.\n    "
            + "You can specify a name in your compose config YAML file under these keys:\n    "
            + "config:stack:project_name\n    "
        )
    return project_name


def ensure_project_name(compose_config: Dict[str, Any]) -> None:
    """
    Ensure the project name is set in the compose configuration dictionary.
    """
    if 'config' not in compose_config:
        compose_config['config'] = {}
    if 'stack' not in compose_config['config']:
        compose_config['config']['stack'] = {}
    if 'project_name' not in compose_config['config']['stack']:
        compose_config['config']['stack']['project_name'] = get_project_name(compose_config)
