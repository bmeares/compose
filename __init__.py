#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Manage Meerschaum environments with Compose.
"""

import pathlib

from meerschaum.utils.typing import SuccessTuple, Optional, List, Any
from meerschaum.plugins import add_plugin_argument, make_action, from_plugin_import

from .sync import sync

__version__ = '2.0.0'
required = ['python-dotenv', 'envyaml']


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
add_plugin_argument(
    '--isolated', action='store_true', help=(
        "Execute Meerschaum commands in subprocesses for best isolation."
    )
)


@make_action(daemon=False)
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
    _do_subaction = from_plugin_import('compose.subactions', '_do_subaction')
    subaction = action[0] if action else 'default'
    return _do_subaction(
        subaction,
        action=(action or []),
        file=file,
        env_file=env_file,
        debug=debug,
        **kwargs
    )


_get_subactions = from_plugin_import('compose.subactions', 'get_subactions')
def complete_compose(action: Optional[List[str]] = None, **kwargs):
    subactions = _get_subactions()
    if not action:
        return subactions

    possibilities = []
    for subaction in subactions:
        if subaction.startswith(action[0]) and action[0] != subaction:
            possibilities.append(subaction)

    return possibilities
