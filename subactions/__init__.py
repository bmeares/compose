#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
The entrypoint for subactions to the `compose` command.
"""

import os
import sys
import copy
import pathlib
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
    from meerschaum.config import replace_config, _config
    from meerschaum.config._default import default_config
    from meerschaum.config.environment import replace_env
    from meerschaum.plugins import (
        from_plugin_import,
        unload_plugins,
        load_plugins,
        get_plugins_names,
    )
    from meerschaum.utils.warnings import dprint

    get_env_dict = from_plugin_import('compose.utils.config', 'get_env_dict')
    init = from_plugin_import('compose.utils', 'init')
    subaction_function = (
        _original_subaction_functions.get(
            subaction,
            _original_subaction_functions['default']
        )
    )

    compose_config = init(debug=debug, **kwargs) if subaction != 'init' else {}
    config = (
        copy.deepcopy(compose_config.get('config', default_config))
        if subaction != 'init'
        else _config()
    )
    env = get_env_dict(
        (
            compose_config
            if compose_config
            else {'config': config}
        )
    )
    need_unload = 'MRSM__COMPOSE_CONFIG' not in os.environ

    old_plugins_names = get_plugins_names()
    if need_unload:
        if debug:
            dprint("Compose: Unloading plugins before replacing config.", icon=False)

        compose_mod = sys.modules.get('plugins.compose', None)
        unload_plugins(
            [plugin_name for plugin_name in old_plugins_names if plugin_name != 'compose'],
            debug=debug,
        )
        _ = sys.modules.pop('plugins', None)

    if debug:
        dprint("Compose: Replacing config.", icon=False)

    with replace_config(config):
        with replace_env(env):
            new_plugin_names = get_plugins_names() if subaction != 'init' else []
            if subaction != 'init':
                if debug:
                    dprint(f"Compose: Loading plugins: {new_plugin_names}", icon=False)

                load_plugins(debug=debug)
                new_plugins_mod = sys.modules.get('plugins', None)
                if new_plugins_mod is not None:
                    setattr(new_plugins_mod, 'compose', compose_mod)

            if debug:
                _subaction_name = subaction_function.__name__.lstrip('_').replace('_',  ' ')
                dprint(
                    f"Compose: Calling `{_subaction_name}`...",
                    icon=False
                )

            success, msg = subaction_function(compose_config, debug=debug, **kwargs)

            if need_unload and subaction != 'init':
                if debug:
                    dprint("Compose: Unloading project plugins.", icon=False)
                unload_plugins(
                    [plugin_name for plugin_name in new_plugin_names if plugin_name != 'compose'],
                    debug=debug,
                )

    if need_unload:
        if debug:
            dprint("Compose: Loading back existing plugins.")
        load_plugins(debug=debug)
    return success, msg


_subaction_partials = {
    f"_compose_{_subaction}": _partial(_do_subaction, _subaction)
    for _subaction in _subactions
}
globals().update(_subaction_partials)
