#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Read the configuration files.
"""

import os
import pathlib
import json
import pickle
import platform

import meerschaum as mrsm
from meerschaum.utils.typing import Optional, Union, Dict, Any, List
from meerschaum.utils.warnings import warn, info
from meerschaum.config._paths import PLUGINS_RESOURCES_PATH
from meerschaum.plugins import from_plugin_import
from meerschaum.utils.misc import items_str

COMPOSE_KEYS = [
    'root_dir',
    'plugins_dir',
    'plugins',
    'sync',
    'config',
    'environment',
    'project_name',
    'pipes',
    'jobs',
]
DEFAULT_COMPOSE_FILE_CANDIDATES = ['mrsm-compose.yaml', 'mrsm-compose.yml']
CONFIG_METADATA: Dict[str, Any] = {}


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
        return file.resolve() if file.exists() else None
    found_candidates = []
    for candidate_name in DEFAULT_COMPOSE_FILE_CANDIDATES:
        candidate_path = pathlib.Path(candidate_name).resolve()
        if candidate_path.exists():
            found_candidates.append(candidate_path)
    if len(found_candidates) > 1:
        warn(f"Found multiple YAML files. Compose will use this file:\n{found_candidates[0]}.")
    elif len(found_candidates) == 0:
        return None
    return found_candidates[0].resolve()


def read_compose_config(
    compose_file_path: pathlib.Path,
    env_file: Optional[pathlib.Path] = None,
    debug: bool = False,
) -> Union[Dict[str, Any], None]:
    """
    Read the compose file and only include the top-level keys from `COMPOSE_KEYS`.

    Parameters
    ----------
    compose_file_path: pathlib.Path
        The file path to the compose file.
        This file must be verified to exist.

    env_file: Optional[pathlib.Path], default None
        Use a specific environment file.
        Defaults to `./.env`.

    Returns
    -------
    The contents of the compose YAML file as a dictionary.
    """
    from meerschaum.config._read_config import search_and_substitute_config

    ensure_project_name = from_plugin_import('compose.utils.stack', 'ensure_project_name')

    envyaml = mrsm.attempt_import('envyaml', venv='compose')
    try:
        env = envyaml.EnvYAML(
            yaml_file = compose_file_path,
            env_file = env_file,
            include_environment = True,
            flatten = False,
            strict = True,
        )
    except ValueError as ve:
        ### Yes, this is a hacky way to build the message,
        ### but it's the best solution for the time being.
        missing_vars = (
            str(ve)
            .split(' variables ', maxsplit=1)[-1]
            .split(' are not ', maxsplit=1)[0]
            .replace(' ', '')
            .split(',')
        )

        singular = len(missing_vars) == 1
        message = (
            items_str(missing_vars)
            + ' ' + ('is' if singular else 'are') + ' not defined!\n'
            + '     Using ' + ('an' if singular else '')
            + ' empty string' + ('' if singular else 's') + ' for '
            + ('this variable' if singular else 'these variables')
            + '.'
        )
        warn(message, stack=False)
        
        for var in missing_vars:
            os.environ[var.lstrip('$')] = ''

        env = envyaml.EnvYAML(
            yaml_file = compose_file_path,
            env_file = env_file,
            include_environment = True,
            flatten = False,
            strict = True,
        )

    compose_config = {k: env[k] for k in COMPOSE_KEYS if k in env}
    compose_cf = compose_config.get('config', {})
    if compose_cf:
        compose_cf = search_and_substitute_config(compose_cf)
        compose_config['config'] = compose_cf
    plugins_dir_paths = get_dir_paths(compose_config, 'plugins')
    for plugins_dir_path in plugins_dir_paths:
        if not plugins_dir_path.exists():
            plugins_dir_path.mkdir(parents=True, exist_ok=True)

    ### Add metadata keys (project_name, root_dir, plugin_dir, __file__).
    compose_config['__file__'] = compose_file_path
    ensure_dir_keys(compose_config)
    ensure_project_name(compose_config)
    return compose_config


def ensure_dir_keys(compose_config) -> None:
    """
    Add the keys `root_dir` and `plugins_dir`.
    """
    compose_config['root_dir'] = get_dir_paths(compose_config, 'root')[0]
    compose_config['plugins_dir'] = get_dir_paths(compose_config, 'plugins')
    plugins_dir_paths = get_dir_paths(compose_config, 'plugins')


def get_dir_paths(compose_config: Dict[str, Any], dir_name: str) -> List[pathlib.Path]:
    """
    Return the absolute paths for the configured plugins directory.
    Throw a warning if multiple values are configured.

    Parameters
    ----------
    compose_config: pathlib.Path
        The compose configuration dictionary.

    dir_name: str
        The name of the directory to be resolved.
        Values include 'root' and 'plugins'.

    Returns
    -------
    The absolute path to the configured directory.
    """
    compose_file_path = compose_config.get('__file__', None)
    old_cwd = os.getcwd()
    if compose_file_path is not None:
        os.chdir(compose_file_path.parent)

    configured_dir = compose_config.get(f'{dir_name}_dir', -1)
    env_dir = compose_config.get('environment', {}).get(f'MRSM_{dir_name.upper()}_DIR', None)
    local_dir_path = (
        compose_file_path.parent / dir_name
    ) if compose_file_path is not None else None

    if isinstance(env_dir, str):
        if env_dir.lstrip().startswith('['):
            env_dir_paths = [
                pathlib.Path(env_path_str).resolve()
                for env_path_str in json.loads(env_dir)
            ]
        else:
            env_dir_paths = [pathlib.Path(env_dir).resolve()]
    else:
        env_dir_paths = []

    if configured_dir == -1:
        configured_dir_vals = []
    elif isinstance(configured_dir, list):
        configured_dir_vals = configured_dir
    else:
        configured_dir_vals = [configured_dir]

    configured_dir_paths = []
    for configured_dir_val in configured_dir_vals:
        if configured_dir_val in ('', None) and dir_name == 'plugins':
            info(
                "A null value for `plugins_dir` will include your regular Meerschaum plugins.\n"
                + "    This will be less isolated than project-specific plugins directories."
            )
            path = PLUGINS_RESOURCES_PATH
        else:
            path = pathlib.Path(configured_dir_val).resolve()
        if path not in configured_dir_paths:
            configured_dir_paths.append(path)

    paths = (
        configured_dir_paths
        + ([local_dir_path.resolve()] if local_dir_path is not None else [])
        + env_dir_paths
    )

    unique_paths = []
    for path in paths:
        real_path = pathlib.Path(os.path.realpath(path)).resolve()
        if real_path not in unique_paths:
            unique_paths.append(real_path)
    existing_unique_paths = [path for path in unique_paths if path.exists()]

    if compose_file_path is not None:
        os.chdir(old_cwd)

    if (
        len(existing_unique_paths) > 1
        and
        dir_name != 'plugins'
    ):
        path = unique_paths[0]
        warn(
            f"Detected multiple values for {dir_name}_dir.\n   "
            + f"Compose will use '{path}' for {dir_name}_dir.",
            stack = False,
        )
        return [path]

    return unique_paths


def get_env_dict(compose_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a dictionary of environment variables.
    """
    env_dict = {}

    if platform.system() == 'Windows':
        app_data = os.environ.get('AppData', '')
        home = os.environ.get('HOME', pathlib.Path.home().as_posix())
        homepath = os.environ.get('HOMEPATH', home)
        env_dict.update({
            'AppData': app_data,
            'HOME': home,
            'HOMEPATH': homepath,
        })
        env_dict.update(os.environ)

    term = os.environ.get('TERM', None)
    if term:
        env_dict['TERM'] = term

    root_dir_path = compose_config.get('root_dir', None)
    if root_dir_path is not None:
        env_dict['MRSM_ROOT_DIR'] = root_dir_path.as_posix()

    plugins_dir_path = compose_config.get('plugins_dir', None)
    if plugins_dir_path:
        env_dict['MRSM_PLUGINS_DIR'] = (
            plugins_dir_path.as_posix()
            if not isinstance(plugins_dir_path, list)
            else json.dumps(
                [path.as_posix() for path in plugins_dir_path],
                separators=(',', ':'),
            )
        )

    config = compose_config.get('config', None)
    if config:
        env_dict['MRSM_CONFIG'] = json.dumps(config, separators=(',', ':'))

    if compose_config.get('environment', None):
        env_dict.update(compose_config['environment'])

    none_keys = [key for key, val in env_dict.items() if val is None]
    for key in none_keys:
        env_dict[key] = ''

    return env_dict


def write_patch(compose_config: Dict[str, Any], debug: bool = False) -> None:
    """
    Write the patch files to the configured patch directory.
    """
    from meerschaum.config._edit import write_config
    root_dir_path = compose_config['root_dir']
    patch_dir_path = root_dir_path / 'permanent_patch_config'
    patch_dir_path.mkdir(exist_ok=True)
    write_config(compose_config.get('config', {}), patch_dir_path, debug=debug)


def init_root(compose_config: Dict[str, Any], debug: bool = False) -> bool:
    """
    Initialize the Meerschaum root directory.
    """
    from plugins.compose.utils import run_mrsm_command
    from plugins.compose.utils.plugins import get_installed_plugins
    root_dir_path = compose_config['root_dir']
    fresh = False
    if not root_dir_path.exists():
        fresh = True
        root_dir_path.mkdir(exist_ok=True)
        info(
            "Initializing Meerschaum root directory:\n    "
            f"{root_dir_path}\n    "
            "This should only take a few seconds..."
        )

    success, message = run_mrsm_command(
        ['show', 'version', '--no-daemon'],
        compose_config,
        capture_output=True,
        debug=debug,
    )

    if fresh:
        if get_installed_plugins(compose_config, debug=debug):
            info("Installing required packages for plugins...")
            run_mrsm_command(
                ['install', 'required'],
                compose_config,
                capture_output=False,
                debug=debug,
            )

    ### Update the cache after building the in-memory config.
    if config_has_changed(compose_config):
        write_config_cache(compose_config)

    return success


def init_env(
        compose_file_path: pathlib.Path,
        env_file: Optional[pathlib.Path] = None
    ) -> None:
    """
    Initialize the local environment from the dotfile.

    Parameters
    ----------
    env_file: Optional[pathlib.Path], default None
        The path to the the environment dotfile.
        Infer `.env` if `env_file` is `None`.
    """
    from dotenv import load_dotenv
    old_cwd = os.getcwd()
    os.chdir(compose_file_path.parent)
    if env_file is None:
        env_file = '.env'
    env_path = compose_file_path.parent / env_file
    try:
        if env_path.exists():
            load_dotenv(env_file)
    except Exception as e:
        warn(f"Failed to load '{env_path}':\n{e}")
    os.chdir(old_cwd)


def get_config_cache_path(compose_config: Dict[str, Any]) -> pathlib.Path:
    """
    Return the file path to the config cache file.
    """
    root_dir_path = compose_config['root_dir']
    return root_dir_path / '.compose-cache.pkl'


def write_config_cache(compose_config: Dict[str, Any]) -> None:
    """
    Write the current compose configuration to a cache file.
    """
    config_cache_path = get_config_cache_path(compose_config) 

    with open(config_cache_path, 'wb') as f:
        pickle.dump(hash_config(compose_config), f)


def read_config_cache(compose_config: Dict[str, Any]) -> Union[int, None]:
    """
    Read and return the cached config metadata.
    If no cache exists, return None.
    """
    config_cache_path = get_config_cache_path(compose_config)
    if not config_cache_path.exists():
        return None
    with open(config_cache_path, 'rb') as f:
        config_cache = pickle.load(f)
    return config_cache


def config_has_changed(compose_config: Dict[str, Any]) -> bool:
    """
    Check if the in-memory configuration is the same as the last cached version.
    """
    if 'config_has_changed' in CONFIG_METADATA:
        return CONFIG_METADATA['config_has_changed']
    config_cache = read_config_cache(compose_config)
    hashed_config = hash_config(compose_config)
    has_changed = (config_cache != hashed_config)
    CONFIG_METADATA['config_has_changed'] = has_changed
    return has_changed


def hash_config(compose_config: Dict[str, Any]) -> str:
    """
    Compute the hash value for the configuration dictionary.
    """
    import hashlib
    return hashlib.sha256(
        bytes(
            json.dumps(compose_config, sort_keys=True, default=str),
            encoding = 'utf-8',
        )
    ).hexdigest()
