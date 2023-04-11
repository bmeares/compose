#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Define `mrsm compose run`.
"""

from meerschaum.utils.typing import SuccessTuple, Dict, Any, Optional, List

def compose_run(**kw) -> SuccessTuple:
    """
    Run a single pass of the compose file (i.e. `mrsm compose up --no-jobs --verify`).
    """
    from plugins.compose.subactions import compose_up
    kw.update({
        'no_jobs': True,
        'verify': True,
    })
    return compose_up(**kw)

