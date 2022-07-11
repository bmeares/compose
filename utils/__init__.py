#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Utility functions.
"""

import subprocess
from meerschaum.utils.typing import List, Dict, Any
from meerschaum.utils.packages import run_python_package

def run_mrsm_command(
        args: List[str],
        compose_config: Dict[str, Any],
        capture_output: bool = True,
        debug: bool = False,
        **kw
    ) -> subprocess.Popen:
    from plugins.compose.utils.debug import get_debug_args
    from plugins.compose.utils.config import get_env_dict, write_patch
    #  write_patch(compose_config, debug=debug)
    as_proc = True if 'as_proc' not in kw else kw.pop('as_proc')
    return run_python_package(
        'meerschaum', args + get_debug_args(debug),
        env = get_env_dict(compose_config),
        capture_output = capture_output,
        as_proc = as_proc,
        debug = debug,
        **kw
    )

