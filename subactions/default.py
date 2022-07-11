#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Pass all other subactions to `mrsm stack`.
"""

from meerschaum.utils.typing import SuccessTuple, Dict, Any, Optional, List

def compose_default(
        compose_config: Dict[str, Any],
        action: Optional[List[str]] = None,
        sysargs: Optional[List[str]] = None,
        debug: bool = False,
        **kw,
    ) -> SuccessTuple:
    """
    Pass other subactions to `mrsm stack`.
    """
    from plugins.compose.utils import run_mrsm_command
    #  if not action:
        #  return False, (
            #  "No command specified.\n    Try passing a `docker-compose` actions, e.g. `compose ps`."
        #  )

    success = run_mrsm_command(
        #  ['stack'] + sysargs[sysargs.index('compose')+1:],
        ['stack'] + action,
        compose_config,
        capture_output = False,
        debug = debug,
    ).wait() == 0
    msg = "Success" if success else "Failed to run sub"

    return True, "Success"
