#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Utility functions.
"""

import subprocess
import copy
import pathlib
import shlex
from typing import List, Dict, Any, Optional, Union

import meerschaum as mrsm
from meerschaum.plugins import from_plugin_import
get_debug_args = from_plugin_import('compose.utils.debug', 'get_debug_args')
get_env_dict = from_plugin_import('compose.utils.config', 'get_env_dict')
get_project_name = from_plugin_import('compose.utils.stack', 'get_project_name')


def run_mrsm_command(
    args: Union[List[str], str],
    compose_config: Dict[str, Any],
    capture_output: bool = False,
    debug: bool = False,
    _subprocess: Optional[bool] = None,
    _replace: bool = True,
    **kw
) -> mrsm.SuccessTuple:
    """
    Run a Meerschaum command in a subprocess.
    """
    from meerschaum.config.environment import replace_env
    from meerschaum.utils.packages import run_python_package
    from meerschaum.config import replace_config
    from meerschaum.config.paths import replace_root_dir, ROOT_DIR_PATH
    from meerschaum._internal.entry import entry

    project_name = get_project_name(compose_config)
    if isinstance(args, str):
        args = shlex.split(args)

    sysargs = (
        args
        + (get_debug_args(debug) if '--debug' not in args else [])
        + (
            ['--tags', project_name]
            if (
                '--tags' not in args
                and
                '-t' not in args
                and not ' '.join(args).startswith('stack ')
            )
            else []
        )
    )

    if _subprocess is None:
        _subprocess = compose_config.get('isolation', None) == 'subprocess'

    if _subprocess:
        _replace = True

    config = copy.deepcopy(compose_config.get('config', {})) if _replace else None
    env = get_env_dict(compose_config) if _replace else None
    root_dir_path = compose_config.get('root_dir', ROOT_DIR_PATH) if _replace else None

    if capture_output or _subprocess:
        success = run_python_package(
            'meerschaum',
            sysargs,
            env=env,
            capture_output=capture_output,
            as_proc=False,
            venv=None,
            foreground=True,
            debug=debug,
            **kw
        ) == 0
        if success:
            return success, "Success"
        return False, f"Failed to execute sysargs:\n{sysargs}"

    with replace_root_dir(root_dir_path):
        with replace_config(config):
            with replace_env(env):
                success, msg = entry(sysargs, _use_cli_daemon=True)

    return success, msg


def init(
    file: Optional[pathlib.Path] = None,
    env_file: Optional[pathlib.Path] = None,
    isolated: bool = False,
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
    from meerschaum.plugins import inject_plugin_path
    (
        infer_compose_file_path,
        init_env,
        init_root,
        read_compose_config,
    ) = from_plugin_import(
        'compose.utils.config',
        'infer_compose_file_path',
        'init_env',
        'init_root',
        'read_compose_config',
    )
    compose_file_path = infer_compose_file_path(file)
    if compose_file_path is None:
        raise Exception(
            "No compose file could be found.\n    "
            + "Create a file mrsm-compose.yaml or specify a path with `--file`."
        )

    init_env(compose_file_path, env_file)
    compose_config = read_compose_config(
        compose_file_path,
        env_file=env_file,
        isolated=isolated,
        debug=debug,
    )
    init_root(compose_config)
    root_dir_path = compose_config['root_dir']
    plugins_resources_path = root_dir_path / '.internal' / 'plugins'
    internal_plugins_compose_path = plugins_resources_path / 'compose'
    current_package_file = pathlib.Path(__file__).parent.parent
    if not internal_plugins_compose_path.exists():
        inject_plugin_path(current_package_file, plugins_resources_path=plugins_resources_path)
    return compose_config
