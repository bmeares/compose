#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
The entrypoint for subactions to the `compose` command.
"""

import os
import pathlib
import copy
from functools import partial as _partial

from meerschaum.plugins import from_plugin_import

def get_subactions():
    return [
        filename[:(-1 * len('.py'))]
        for filename in os.listdir(pathlib.Path(__file__).parent)
        if filename.endswith('.py') and not filename.startswith('_')
    ]

_subactions = get_subactions()

_original_subaction_functions = {
    _subaction: from_plugin_import(f'compose.subactions.{_subaction}', f"_compose_{_subaction}")
    for _subaction in _subactions
}


def _do_subaction(
    subaction: str,
    debug: bool = False,
    **kwargs
):
    from meerschaum.config import replace_config
    from meerschaum.config._default import default_config
    from meerschaum.config.environment import replace_env
    from meerschaum.plugins import from_plugin_import, unload_plugins, load_plugins, get_plugins_names

    get_env_dict = from_plugin_import('compose.utils.config', 'get_env_dict')
    init = from_plugin_import('compose.utils', 'init')
    subaction_function = (
        _original_subaction_functions.get(
            subaction,
            _original_subaction_functions['default']
        )
    )

    compose_config = init(debug=debug, **kwargs) if subaction != 'init' else {}
    config = copy.deepcopy(compose_config.get('config', default_config))
    env = get_env_dict(
        (
            compose_config
            if compose_config
            else {'config': config}
        )
    )

    old_plugins_names = get_plugins_names()
    unload_plugins([plugin_name for plugin_name in old_plugins_names if plugin_name != 'compose'])

    with replace_config(config):
        with replace_env(env):
            plugins_names = get_plugins_names()
            load_plugins()
            success, msg = subaction_function(compose_config, debug=debug, **kwargs)
            unload_plugins([plugin_name for plugin_name in plugins_names if plugin_name != 'compose'])

    load_plugins()
    return success, msg


_subaction_partials = {
    f"_compose_{_subaction}": _partial(_do_subaction, _subaction)
    for _subaction in _subactions
}
globals().update(_subaction_partials)
