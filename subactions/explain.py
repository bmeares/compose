#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Print out the defined pipes and configuration from the compose file.
"""

import meerschaum as mrsm
from meerschaum.utils.typing import SuccessTuple, Any, Optional, List, Dict
from meerschaum.plugins import from_plugin_import


def _compose_explain(
    compose_config: Dict[str, Any],
    action: Optional[List[str]] = None,
    sysargs: Optional[List[str]] = None,
    nopretty: bool = False,
    debug: bool = False,
    **kw: Any
) -> SuccessTuple:
    """
    Execute Meerschaum actions in the isolated environment.
    """
    (
        build_custom_connectors,
        get_defined_pipes,
        instance_pipes_from_pipes_list,
    ) = from_plugin_import(
        'compose.utils.pipes',
        'build_custom_connectors',
        'get_defined_pipes',
        'instance_pipes_from_pipes_list',
    )
    get_project_name = from_plugin_import('compose.utils.stack', 'get_project_name')

    project_name = get_project_name(compose_config)
    _ = build_custom_connectors(compose_config)
    pipes = get_defined_pipes(compose_config)
    instance_pipes = instance_pipes_from_pipes_list(pipes)

    from meerschaum.utils.warnings import info
    from meerschaum.utils.formatting import get_console
    from meerschaum.utils.formatting._pipes import pipe_repr
    from meerschaum.utils.packages import import_rich, attempt_import
    from meerschaum.config import get_config
    console = get_console()
    _ = import_rich()
    rich_table, rich_json, rich_text, rich_panel, rich_layout = attempt_import(
        'rich.table',
        'rich.json',
        'rich.text',
        'rich.panel',
        'rich.layout',
    )
    from rich import box
    pipe_styles = get_config('formatting', 'pipes', '__repr__', 'ansi', 'styles')

    rows = []
    for instance, pipes in instance_pipes.items():
        instance_panel = rich_panel.Panel(
            rich_text.Text(
                instance, style=pipe_styles['instance']),
            title = 'Instance',
        )
        rows.append({
            'pipe_text': instance_panel,
            'local_text': rich_text.Text(''),
            'remote_text': rich_text.Text(''),
            'end_section': rich_text.Text(''),
        })

        for i, pipe in enumerate(pipes):
            clean_pipe = mrsm.Pipe(**pipe.meta)
            remote_parameters = clean_pipe.parameters
            local_parameters = pipe._attributes['parameters']
            include_remote_parameters = False
            if pipe.temporary:
                registration_status = "🔳 Temporary"
            elif not pipe.id:
                registration_status = "⭕ Not registered"
            elif remote_parameters != local_parameters:
                include_remote_parameters = True
                registration_status = (
                    "❌ Outdated"
                    if {**local_parameters, **remote_parameters} != remote_parameters
                    else "🟨 Params added"
                )
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

    include_remote_col = any([(row.get('remote_text', None) is not None) for row in rows])
    table = rich_table.Table(
        title=f"Pipes in '{project_name}'",
        box=box.MINIMAL,
        show_header=True,
        expand=True,
        collapse_padding=True,
        title_style='bold',
    )

    table.add_column("Defined Pipes")
    table.add_column("Compose Parameters")
    if include_remote_col:
        table.add_column("Remote Parameters")

    for row in rows:
        cols = (
            [
                row.get('pipe_text', rich_text.Text('')),
                row.get('local_text', rich_text.Text('')),
            ]
            + (
                [
                    row.get('remote_text', rich_text.Text('')),
                ]
                if include_remote_col
                else []
            )
        )
        end_section = row.get('end_section', False)
        table.add_row(
            *cols,
            end_section = end_section,
        )
        if not end_section:
            table.add_row('', '')


    console.print(table)

    success, msg = True, "Success"
    return success, msg
