#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Define the `plugin:compose` sync method.
"""

import sys
import json

import meerschaum as mrsm
from meerschaum.utils.typing import SuccessTuple, Any, List
from meerschaum.utils.warnings import dprint, warn


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
    from meerschaum.utils.misc import generate_password
    from meerschaum.utils.process import run_process
    from plugins.compose.utils.stack import get_project_name, ensure_project_name
    from plugins.compose.utils.config import ensure_dir_keys
    from subprocess import call

    compose_config = pipe.parameters.get('compose', {})
    children_meta = pipe.parameters.get('children', [])
    project_name = get_project_name(compose_config)

    return _sync(pipe, **kwargs)

    dill = mrsm.attempt_import('dill')
    sync_source = dill.source.getsource(_sync)

    compose_dir_path = ROOT_DIR_PATH / 'compose'
    compose_project_path = compose_dir_path / project_name
    compose_project_path.mkdir(parents=True, exist_ok=True)
    session_id = generate_password(6)
    output_file_path = compose_project_path / f'.{session_id}-output'

    pipe_attrs = {**pipe.meta, **{'parameters': pipe._attributes.get('parameters', {})}}
    _ = kwargs.pop('sync_method', None)
    if kwargs.get('debug'):
        mrsm.pprint(pipe_attrs)
    code_to_run = (
        "import meerschaum as mrsm\n"  
        + "dill = mrsm.attempt_import('dill')\n\n"
        + sync_source + "\n\n"
        + f"output_file_path = \"\"\"{output_file_path.as_posix()}\"\"\"\n\n"
        + f"kwargs = dill.loads({dill.dumps(kwargs)})\n\n"
        + f"pipe_attrs = dill.loads({dill.dumps(pipe_attrs)})\n\n"
        + "pipe = mrsm.Pipe(**pipe_attrs)\n\n"
        + "success, msg = _sync(pipe, **kwargs)\n\n"
        + "with open(output_file_path, 'wb+') as f:\n"
        + "    dill.dump((success, msg), f)"
    )
    if kwargs.get('debug'):
        dprint(code_to_run)

    rc = run_process(
        [sys.executable, '-c', code_to_run],
        foreground = False,
    )

    if not output_file_path.exists() or rc != 0:
        return False, f"Failed to sync {pipe} in a subprocess."

    with open(output_file_path, 'rb') as f:
        success, msg = dill.load(f)

    try:
        if output_file_path.exists():
            output_file_path.unlink()
    except Exception as e:
        warn(f"Failed to clean up '{output_file_path}':\n{e}")

    return success, msg


def _sync(pipe: mrsm.Pipe, **kwargs):
    """
    Sync the pipe's children one-by-one.
    """
    import time
    from meerschaum.utils.typing import List
    from meerschaum.utils.warnings import warn, info
    from meerschaum.utils.formatting import make_header, UNICODE

    child_successes: List[bool] = []
    child_messages: List[str] = []
    loop_start = time.perf_counter()
    arrow = '⮡' if UNICODE else '->'

    for child_num, child_pipe in enumerate(pipe.children):
        info(f"{pipe}:\n    {arrow} {child_num + 1}. Syncing {child_pipe}...")
        child_pipe_start = time.perf_counter()
        child_success, child_msg = child_pipe.sync(**kwargs)
        child_msg = child_msg.lstrip().rstrip()
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
