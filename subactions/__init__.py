#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
The entrypoint for subactions to the `compose` command.
"""

import os
import pathlib
from functools import partial as _partial

from meerschaum.plugins import from_plugin_import

_subactions = [
    filename[:(-1 * len('.py'))]
    for filename in os.listdir(pathlib.Path(__file__).parent)
    if filename.endswith('.py') and not filename.startswith('_')
]

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
    from meerschaum.config.environment import replace_env
    #  from meerschaum.config.paths import replace_root_dir
    from meerschaum.plugins import from_plugin_import

    get_env_dict = from_plugin_import('compose.utils.config', 'get_env_dict')
    init = from_plugin_import('compose.utils', 'init')
    subaction_function = (
        _original_subaction_functions.get(
            subaction,
            _original_subaction_functions['default']
        )
    )

    compose_config = init(debug=debug) if subaction != 'init' else {}
    
    with replace_config(compose_config.get('config', {})):
        with replace_env(get_env_dict(compose_config)):
            return subaction_function(compose_config, debug=debug, **kwargs)


_subaction_partials = {
    f"_compose_{_subaction}": _partial(_do_subaction, _subaction)
    for _subaction in _subactions
}

globals().update(_subaction_partials)
