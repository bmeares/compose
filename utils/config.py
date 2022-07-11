#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Read the configuration files.
"""

import pathlib
import json
from meerschaum.utils.typing import Optional, Union, Dict, Any, List
from meerschaum.utils.warnings import warn, info
from meerschaum.utils.debug import dprint
from meerschaum.utils.formatting import pprint
from meerschaum.utils.packages import run_python_package

COMPOSE_KEYS = ['MRSM_ROOT_DIR', 'plugins', 'sync', 'config']
DEFAULT_COMPOSE_FILE_CANDIDATES = ['mrsm-compose.yaml', 'mrsm-compose.yml']

def infer_compose_file_path(file: Optional[pathlib.Path] = None) -> Union[pathlib.Path, None]:
    """
    Return the file path to a valid compose file or `None` if nothing exists.

    Parameters
    ----------
    file: Optional[pathlib.Path], default None
        If a specific path is provided, only check if it exists.
        Otherwise go through the candidates and see if any exist.

    Returns
    -------
    The file path to a compose file if it exists, else `None`.
    """
    if file is not None:
        return file if file.exists() else None
    found_candidates = []
    for candidate_name in DEFAULT_COMPOSE_FILE_CANDIDATES:
        candidate_path = pathlib.Path(candidate_name).resolve()
        if candidate_path.exists():
            found_candidates.append(candidate_path)
    if len(found_candidates) > 1:
        warn(f"Found multiple YAML files. Compose will use this file:\n{found_candidates[0]}.")
    elif len(found_candidates) == 0:
        return None
    return found_candidates[0]


def read_compose_config(
        compose_file_path: pathlib.Path,
        debug: bool = False,
    ) -> Union[Dict[str, Any], None]:
    """
    Read the compose file and only include the top-level keys from `COMPOSE_KEYS`.

    Parameters
    ----------
    compose_file_path: pathlib.Path
        The file path to the compose file.
        This file must be verified to exist.
    """
    from plugins.compose.utils.stack import ensure_project_name
    from envyaml import EnvYAML
    env = EnvYAML(compose_file_path)
    compose_config = {k: env[k] for k in COMPOSE_KEYS if k in env}
    ensure_project_name(compose_config)
    if debug:
        dprint("Compose config:")
        pprint(compose_config)
    return compose_config


def get_root_dir_path(compose_config: Dict[str, Any]) -> pathlib.Path:
    """
    Return the absolute path for the configured root directory.
    """
    return pathlib.Path(compose_config.get('MRSM_ROOT_DIR', './root')).resolve()


def get_env_dict(compose_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a dictionary of environment variables.
    """
    return {
        'MRSM_ROOT_DIR': str(get_root_dir_path(compose_config)),
        #  'MRSM_CONFIG': json.dumps(compose_config.get('config', {})),
    }


def write_patch(compose_config: Dict[str, Any], debug: bool = False) -> None:
    """
    Write the patch files to the configured patch directory.
    """
    from meerschaum.config._edit import write_config
    root_dir_path = get_root_dir_path(compose_config)
    patch_dir_path = root_dir_path / 'permanent_patch_config'
    if not root_dir_path.exists():
        root_dir_path.mkdir(exist_ok=True)
        init_root(compose_config, debug=debug)
        info(
            "Initializing Meerschaum root directory:\n    "
            + f"{root_dir_path}\n    "
            + "This should only take a few seconds..."
        )
    patch_dir_path.mkdir(exist_ok=True)
    print("Writing config")
    write_config(compose_config.get('config', {}), patch_dir_path, debug=debug)


def init_root(compose_config: Dict[str, Any], debug: bool = False) -> bool:
    from plugins.compose.utils import run_mrsm_command
    return run_mrsm_command(
        ['show', 'version'], compose_config, debug=debug,
    ).wait() == 0


def init_env(env_file: Optional[pathlib.Path] = None) -> None:
    """
    Initialize the local environment from the dotfile.

    Parameters
    ----------
    env_file: Optional[pathlib.Path], default None
        The path to the the environment dotfile.
        Infer `.env` if `env_file` is `None`.
    """
    from dotenv import load_dotenv
    load_dotenv(env_file)


