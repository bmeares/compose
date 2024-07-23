#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

from meerschaum.connectors import Connector, make_connector

@make_connector
class TestConnector(Connector):
    pass
