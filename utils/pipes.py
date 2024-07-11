#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Utilities for managing defined pipes.
"""

from typing import List, Dict, Any, Union
import meerschaum as mrsm

def get_defined_pipes(
        compose_config: Dict[str, Any],
    ) -> List[mrsm.Pipe]:
    """
    Return a list of the Pipes defined in `mrsm-compose.yaml`.

    Parameters
    ----------
    compose_config: Dict[str, Any]
        The Meerschaum compose configuration dictionary.

    Returns
    -------
    A list of pipes.
    """
    from plugins.compose.utils.stack import get_project_name
    from meerschaum.config import get_config
    import copy
    project_name = get_project_name(compose_config)
    default_instance = compose_config.get(
        'config',
        {}
    ).get(
        'meerschaum',
        {}
    ).get(
        'instance',
        get_config('meerschaum', 'instance')
    )
    sync_pipes_meta = compose_config.get('sync', {}).get('pipes', [])
    global_pipes_meta = compose_config.get('pipes', [])
    _pipes_meta = sync_pipes_meta + global_pipes_meta
    pipes_meta = []
    for _pipe_meta in _pipes_meta:
        pipe_meta = copy.deepcopy(_pipe_meta)
        if 'tags' not in pipe_meta:
            pipe_meta['tags'] = []
        pipe_meta['tags'].append(project_name)
        if not pipe_meta.get('instance', None):
            legacy_mrsm_instance = pipe_meta.get('mrsm_instance', None)
            if not legacy_mrsm_instance:
                pipe_meta['instance'] = default_instance
        pipes_meta.append(pipe_meta)

    return [mrsm.Pipe(**pipe_meta) for pipe_meta in pipes_meta]


def build_custom_connectors(compose_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    This function constructs the custom connectors
    so that they are stored in the in-memory registry.
    """
    custom_connectors_config = compose_config.get(
        'config',
        {}
    ).get(
        'meerschaum',
        {}
    ).get(
        'connectors',
        {}
    )
    if not custom_connectors_config:
        return {}
    custom_connectors = {}
    for typ, labels in custom_connectors_config.items():
        for label, connector_kwargs in labels.items():
            conn_keys = typ + ':' + label
            custom_connectors[conn_keys] = mrsm.get_connector(conn_keys, **connector_kwargs)

    return custom_connectors


def instance_pipes_from_pipes_list(pipes: List[mrsm.Pipe]) -> Dict[str, List[mrsm.Pipe]]:
    """
    Return a dictionary of pipes lists, grouping by instance connector keys.
    """
    from collections import defaultdict
    instance_pipes = defaultdict(lambda: [])
    for pipe in pipes:
        instance_pipes[str(pipe.instance_keys)].append(pipe)
    return instance_pipes
