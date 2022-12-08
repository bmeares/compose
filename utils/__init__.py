#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Utility functions.
"""

import subprocess
import pathlib
from typing import List, Dict, Any, Optional

def run_mrsm_command(
        args: List[str],
        compose_config: Dict[str, Any],
        capture_output: bool = True,
        debug: bool = False,
        **kw
    ) -> subprocess.Popen:
    """
    Run a Meerschaum command in a subprocess.
    """
    from plugins.compose.utils.debug import get_debug_args
    from plugins.compose.utils.config import get_env_dict, write_patch
    from meerschaum.utils.packages import run_python_package
    as_proc = kw.pop('as_proc', True)
    venv = kw.pop('venv', None)
    return run_python_package(
        'meerschaum', args + get_debug_args(debug),
        env = get_env_dict(compose_config),
        capture_output = capture_output,
        as_proc = as_proc,
        venv = venv,
        debug = debug,
        **kw
    )


def init(
        file: Optional[pathlib.Path] = None,
        env_file: Optional[pathlib.Path] = None,
        debug: bool = False,
        **kw: Any
    ) -> Dict[str, Any]:
    """
    Top-level initalization function for subactions.

    Parameters
    ----------
    file: Optional[pathlib.Path], default None
        If a specific path is provided, only check if it exists.
        Otherwise go through the candidates and see if any exist.

    env_file: Optional[pathlib.Path], default None
        Use a specific environment file.
        Defaults to `./.env`.

    Returns
    -------
    The file path to a compose file if it exists, else `None`.
    """
    from plugins.compose.utils.config import (
        infer_compose_file_path,
        init_env,
        init_root,
        read_compose_config,
    )
    compose_file_path = infer_compose_file_path(file)
    if compose_file_path is None:
        raise Exception(
            "No compose file could be found.\n    "
            + "Create a file mrsm-compose.yaml or specify a path with `--file`."
        )
    init_env(compose_file_path, env_file)
    compose_config = read_compose_config(compose_file_path, debug=debug)
    init_root(compose_config)
    return compose_config
