#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Define `mrsm compose run`.
"""

from meerschaum.utils.typing import SuccessTuple, Dict, Any


def _compose_run(
    compose_config: Dict[str, Any],
    **kw
) -> SuccessTuple:
    """
    Run a single pass of the compose file (i.e. `mrsm compose up --no-jobs --presync`).
    """
    from meerschaum.plugins import from_plugin_import
    _compose_up = from_plugin_import('compose.subactions.up', '_compose_up')
    kw.update({
        'no_jobs': True,
        'presync': True,
    })
    return _compose_up(compose_config, **kw)

