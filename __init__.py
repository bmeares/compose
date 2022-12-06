#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Manage Meerschaum environments with Compose.
"""

__version__ = '0.1.0'
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
    compose_debug as _compose_debug,
)

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
    from plugins.compose.utils import init
    from .subactions import compose_default
    compose_config = init(file=file, env_file=env_file, debug=debug, **kw)
    return compose_default(
        compose_config = compose_config,
        action = action,
        file = file,
        env_file = env_file,
        debug = debug,
        **kw
    )
