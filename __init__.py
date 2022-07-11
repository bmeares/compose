#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Manage Meerschaum environments with Compose.
"""

__version__ = '0.0.1'
required = ['python-dotenv', 'envyaml']

import json
import pathlib
from meerschaum.utils.typing import SuccessTuple, Optional, List, Dict, Union, Any
from meerschaum.utils.warnings import warn, info
from meerschaum.utils.debug import dprint
from meerschaum.utils.formatting import pprint
from meerschaum.plugins import add_plugin_argument

add_plugin_argument(
    '--file', '--compose-file', type=pathlib.Path, help=(
        "Specify an alternate compose file \n(default: mrsm-compose.yaml)."
    ),
)
add_plugin_argument(
    '--env-file', type=pathlib.Path, help=(
        "Specify an alternate environment file \n(default: .env)."
    ),
)
from .subactions import (
    compose_up as _compose_up,
    compose_down as _compose_down,
    compose_default as _compose_default,
)
SUBACTIONS = {
    'up': _compose_up,
    'down': _compose_down,
}

def compose(
        action: Optional[List] = None,
        file: Optional[pathlib.Path] = None,
        env_file: Optional[pathlib.Path] = None,
        debug: bool = False,
        **kw
    ) -> SuccessTuple:
    """
    Manage an isolated Meerschaum environment with Meerschaum Compose.
    """
    from plugins.compose.utils.config import (
        infer_compose_file_path, read_compose_config, init_env, init_root,
    )
    init_env(env_file)
    compose_file_path = infer_compose_file_path(file)
    if compose_file_path is None:
        return False, (
            "No compose file could be found.\n    "
            + "Create a file mrsm-compose.yaml or specify a path with `--file`."
        )
    compose_config = read_compose_config(compose_file_path, debug=debug)
    init_root(compose_config)
    #  if not action or action[0] not in SUBACTIONS:
        #  return False, (
            #  "Please choose one of the following for `mrsm compose`:\n"
            #  + '\n  - '.join(sorted(SUBACTIONS.keys()))
        #  )
    subaction_function = (
        SUBACTIONS.get(action[0], _compose_default)
        if action else _compose_default
    )
    return subaction_function(
        compose_config,
        action = action[1:] if subaction_function != _compose_default else action,
        file = file,
        env_file = env_file,
        debug = debug,
        **kw
    )
