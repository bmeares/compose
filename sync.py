#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Define the `plugin:compose` sync method.
"""

import time

import meerschaum as mrsm
from meerschaum.utils.typing import SuccessTuple, Any, List
from meerschaum.utils.warnings import warn, info
from meerschaum.utils.formatting import make_header, UNICODE


def sync(
    pipe: mrsm.Pipe,
    **kwargs: Any
) -> SuccessTuple:
    """
    Sync the pipe's children in a subprocess.
    """
    from meerschaum.actions import get_action
    from meerschaum.config.paths import ROOT_DIR_PATH
    from meerschaum.utils.yaml import yaml
    from plugins.compose.utils.stack import get_project_name
    compose_config = pipe.parameters.get('compose', {})
    project_name = get_project_name(compose_config)

    compose_dir_path = ROOT_DIR_PATH / 'compose'
    compose_dir_path.mkdir(exist_ok=True)
    compose_yaml_path = compose_dir_path / 'mrsm-compose.yaml'

    compose_run = get_action(['compose', 'run'])
    return compose_run()

def _sync(
    pipe: mrsm.Pipe,
    **kwargs: Any
) -> SuccessTuple:
    """
    Execute `compose run` for the provided compose project.
    """
    child_successes: List[bool] = []
    child_messages: List[str] = []
    loop_start = time.perf_counter()
    arrow = '⮡' if UNICODE else '->'

    for child_num, child_pipe in enumerate(pipe.children):
        info(f"{pipe}:\n    {arrow} {child_num + 1}. Syncing {child_pipe}...")
        child_pipe_start = time.perf_counter()
        child_success, child_msg = child_pipe.sync(**kwargs)
        child_pipe_duration = time.perf_counter() - child_pipe_start
        mrsm.pprint((child_success, child_msg))

        child_successes.append(child_success)
        child_message = (
            (
                "Successfully synced in "
                if child_success
                else "Failed to sync after "
            ) + f"{round(child_pipe_duration, 2)} seconds:\n"
            + child_msg
        )
        child_messages.append(child_message)

        if not child_success:
            break

    loop_duration = time.perf_counter() - loop_start

    num_synced = len(child_messages)
    success = all(child_successes)
    msg = (
        f"Synced {num_synced} pipe"
        + ('s' if num_synced != 1 else '')
        + f" in {round(loop_duration, 2)} seconds."
    )
    for child_num, (child_pipe, child_message) in enumerate(
        zip(pipe.children, child_messages)
    ):
        child_header = make_header(
            str(child_num + 1) + '. ' + str(child_pipe)
        )
        msg += f"\n\n{child_header}\n{child_message}"
    return success, msg
