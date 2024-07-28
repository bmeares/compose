#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""

"""

from meerschaum.connectors.parse import parse_instance_keys
from meerschaum.utils.typing import Any, SuccessTuple


def compose_deploy(
    mrsm_instance=None,
    **kwargs: Any
) -> SuccessTuple:
    """
    """
    from plugins.compose.utils.pipes import 
    conn = parse_instance_keys(mrsm_instance)

    return True, "Success"
