#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Manage Meerschaum environments with Compose.
"""

__version__ = '1.6.3'
required = ['python-dotenv', 'envyaml']

import json
import pathlib
from meerschaum.utils.typing import SuccessTuple, Optional, List, Dict, Union, Any
from meerschaum.utils.warnings import warn, info
from meerschaum.plugins import add_plugin_argument
from meerschaum.connectors import make_connector

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
add_plugin_argument(
    '--dry', action='store_true', help=(
        "Dry run: update project pipes without syncing."
    ),
)
add_plugin_argument(
    '--drop', '-v', '--volumes', action='store_true', help=(
        "Drop named pipes when running `mrsm compose down`. Analagous to `docker-compose down -v`."
    ),
)
add_plugin_argument(
    '--presync', action='store_true', help=(
        "Run syncs before bringing up the jobs (i.e. used by `mrsm compose run`)."
    )
)
add_plugin_argument(
    '--no-jobs', action='store_true', help=(
        "Exit before starting the background jobs. This is used by `mrsm compose run`."
    )
)

from .sync import sync

from .subactions import (
    compose_up as _compose_up,
    compose_down as _compose_down,
    compose_logs as _compose_logs,
    compose_ps as _compose_ps,
    compose_explain as _compose_explain,
    compose_run as _compose_run,
    compose_init as _compose_init,
)

from .utils import (
    run_mrsm_command,
    init,
)
from .utils.pipes import (
    get_defined_pipes,
    build_custom_connectors,
    instance_pipes_from_pipes_list,
    build_parent_pipe,
)
from .utils.stack import (
    get_project_name, 
    ensure_project_name,
)
from .utils.config import (
    infer_compose_file_path, 
    read_compose_config,
    get_dir_paths,
    get_env_dict,
    init_root,
    init_env,
    get_config_cache_path,
    write_config_cache,
    read_config_cache,
    config_has_changed,
    hash_config,
)


def compose(
        action: Optional[List] = None,
        file: Optional[pathlib.Path] = None,
        env_file: Optional[pathlib.Path] = None,
        debug: bool = False,
        **kwargs: Any
    ) -> SuccessTuple:
    """
    Manage an isolated Meerschaum environment with Meerschaum Compose.
    """
    from .subactions import compose_default
    return compose_default(
        action = action,
        file = file,
        env_file = env_file,
        debug = debug,
        **kwargs
    )


#  def complete_compose(**kwargs: Any) -> List[str]:
    #  """
    #  Return the subactions for `compose`.
    #  """
    #  return ['up', 'down']
