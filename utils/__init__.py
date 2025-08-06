#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Utility functions.
"""

import subprocess
import pathlib
import shlex
from typing import List, Dict, Any, Optional, Union

from meerschaum.plugins import from_plugin_import


def run_mrsm_command(
    args: Union[List[str], str],
    compose_config: Dict[str, Any],
    capture_output: bool = True,
    debug: bool = False,
    **kw
) -> subprocess.Popen:
    """
    Run a Meerschaum command in a subprocess.
    """
    from meerschaum.config.environment import replace_env
    from meerschaum.utils.packages import run_python_package
    from meerschaum.config import replace_config

    get_debug_args = from_plugin_import('compose.utils.debug', 'get_debug_args')
    get_env_dict = from_plugin_import('compose.utils.config', 'get_env_dict')
    get_project_name = from_plugin_import('compose.utils.stack', 'get_project_name')

    project_name = get_project_name(compose_config)
    as_proc = kw.pop('as_proc', True)
    venv = kw.pop('venv', None)
    foreground = kw.pop('foreground', True)
    if isinstance(args, str):
        args = shlex.split(args)

    with replace_env(get_env_dict(compose_config)):
        with replace_config(compose_config.get('config', {})):
            return run_python_package(
                'meerschaum',
                (
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
                ),
                env=get_env_dict(compose_config),
                capture_output=capture_output,
                as_proc=as_proc,
                venv=venv,
                foreground=foreground,
                debug=debug,
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
    from meerschaum.utils.misc import make_symlink
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
        env_file = env_file,
        debug = debug,
    )
    init_root(compose_config)
    root_dir_path = compose_config['root_dir']
    internal_plugins_compose_path = root_dir_path / '.internal' / 'plugins' / 'compose'
    current_package_file = pathlib.Path(__file__).parent.parent
    if not internal_plugins_compose_path.exists():
        internal_plugins_compose_path.parent.mkdir(parents=True, exist_ok=True)
        symlink_success, symlink_msg = make_symlink(
            current_package_file,
            internal_plugins_compose_path,
        )
        if not symlink_success:
            raise EnvironmentError(
                f"Failed to symlink `compose` into '{root_dir_path}':\n{symlink_msg}"
            )

    return compose_config
