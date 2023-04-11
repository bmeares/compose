#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Print out the defined pipes and configuration from the compose file.
"""

import meerschaum as mrsm
from meerschaum.utils.typing import SuccessTuple, Dict, Any, Optional, List

def compose_explain(
        action: Optional[List[str]] = None,
        sysargs: Optional[List[str]] = None,
        nopretty: bool = False,
        debug: bool = False,
        **kw,
    ) -> SuccessTuple:
    """
    Execute Meerschaum actions in the isolated environment.
    """
    import json
    from plugins.compose.utils import run_mrsm_command, init
    from plugins.compose.utils.pipes import (
        build_custom_connectors, get_defined_pipes,
        instance_pipes_from_pipes_list,
    )
    from plugins.compose.utils.stack import get_project_name

    compose_config = init(debug=debug, **kw)
    project_name = get_project_name(compose_config)
    custom_connectors = build_custom_connectors(compose_config)
    pipes = get_defined_pipes(compose_config)
    instance_pipes = instance_pipes_from_pipes_list(pipes)

    from meerschaum.utils.warnings import info
    from meerschaum.utils.formatting import get_console
    from meerschaum.utils.formatting._pipes import pipe_repr
    from meerschaum.utils.packages import import_rich, attempt_import
    console = get_console()
    rich = import_rich()
    rich_table, rich_json, rich_text, rich_panel, rich_layout = attempt_import(
        'rich.table',
        'rich.json',
        'rich.text',
        'rich.panel',
        'rich.layout',
    )
    from rich import box

    rows = []
    for instance, pipes in instance_pipes.items():
        for i, pipe in enumerate(pipes):
            clean_pipe = mrsm.Pipe(**pipe.meta)
            remote_parameters = clean_pipe.parameters
            local_parameters = pipe._attributes['parameters']
            include_remote_parameters = False
            if pipe.temporary:
                registration_status = "🔳 Temporary"
            elif not pipe.id:
                registration_status = "⭕ Not registered"
            elif remote_parameters != pipe._attributes['parameters']:
                registration_status = "❌ Outdated"
                include_remote_parameters = True
            else:
                registration_status = "✅ Up-to-date"

            exists_status = "🟢 Exists" if pipe.exists(debug=debug) else "🔴 Does not exist"

            end_section = (i == (len(pipes) - 1))

            status_text = rich_text.Text(f"\n\n{registration_status}\n{exists_status}\n")
            pipe_text = pipe_repr(pipe, as_rich_text=True)
            pipe_text.append(status_text)
            local_text = rich_json.JSON.from_data(local_parameters, default=str)
            remote_text = (
                rich_json.JSON.from_data(remote_parameters, default=str)
                if include_remote_parameters
                else None
            )

            rows.append({
                'pipe_text': pipe_text,
                'local_text': local_text,
                'remote_text': remote_text,
                'end_section': end_section,
            })

    include_remote_col = any([(row['remote_text'] is not None) for row in rows])
    table = rich_table.Table(
        title = f"Pipes in '{project_name}'",
        box = box.MINIMAL,
        show_header = True,
        expand = True,
        collapse_padding = True,
    )

    table.add_column(f"Defined Pipes")
    table.add_column("Compose Parameters")
    if include_remote_col:
        table.add_column("Remote Parameters")

    for row in rows:
        cols = (
            [
                row['pipe_text'],
                row['local_text'],
            ]
            + (
                [
                    (
                        row['remote_text']
                        if row['remote_text'] is not None
                        else rich_text.Text("✅ Up-to-date")
                    ),
                ]
                if include_remote_col
                else []
            )
        )
        end_section = row['end_section']
        table.add_row(
            *cols,
            end_section = end_section,
        )
        if not end_section:
            table.add_row('', '')


    config_panel = rich_panel.Panel(
        rich_json.JSON.from_data(compose_config.get('config')),
        title = f"MRSM_CONFIG for '{project_name}'",
        box = box.MINIMAL,
    )

    console.print(config_panel)
    console.print(table)

    success, msg = True, "Success"
    return success, msg
