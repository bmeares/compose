#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Manage Meerschaum environments with Compose.
"""

__version__ = '0.0.1'
required = ['python-dotenv', 'envyaml']

import pathlib
from meerschaum.utils.typing import SuccessTuple, Optional, List
from meerschaum.utils.warnings import warn, info
from meerschaum.plugins import add_plugin_argument

add_plugin_argument(
    '--env-file', type=pathlib.Path, help=(
        "Specify an alternate environment file."
    ),
)

COMPOSE_KEYS = [
    'MRSM_ROOT_DIR', 'plugins', 'sync', 'config',
]

def compose(
        action: Optional[List] = None,
        env_file: Optional[pathlib.Path] = None,
        debug: bool = False,
        **kw
    ) -> SuccessTuple:
    """
    Manage an isolated Meerschaum environment with Meerschaum Compose.
    """
    import json
    from dotenv import load_dotenv
    load_dotenv(env_file)
    try:
        compose_file_path = pathlib.Path(action[0]).resolve()
    except Exception as e:
        compose_file_path = None
    if compose_file_path is None:
        compose_file_path = pathlib.Path('mrsm-compose.yaml').resolve()
    if not compose_file_path.exists():
        return False, f"Compose file does not exist: {compose_file_path}"

    from envyaml import EnvYAML
    env = EnvYAML(compose_file_path)
    compose_config = {k: env[k] for k in COMPOSE_KEYS if k in env}
    root_dir_path = pathlib.Path(compose_config.get('MRSM_ROOT_DIR', './root')).resolve()
    if not root_dir_path.exists():
        root_dir_path.mkdir(exist_ok=True)
        info(
            "Initializing Meerschaum root directory:\n    "
            + f"{root_dir_path}\n    "
            + "This should only take a few seconds..."
        )

    debug_args = ['--debug'] if debug else []
    mrsm_env_dict = {
        'MRSM_ROOT_DIR': str(root_dir_path),
        'MRSM_PATCH': json.dumps(compose_config.get('config', {})),
    }

    from meerschaum.utils.packages import run_python_package
    proc = run_python_package(
        'meerschaum', ['show', 'version'] + debug_args,
        env=mrsm_env_dict,
        capture_output=False, as_proc=True,
        debug=debug,
    )
    proc = run_python_package(
        'meerschaum', ['show', 'plugins', '--nopretty'] + debug_args,
        env=mrsm_env_dict,
        capture_output=False, as_proc=True,
        debug=debug,
    )


def _compose_up():
    pass
