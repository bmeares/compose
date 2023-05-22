#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Stress test for pipes.
"""

__version__ = '0.2.1'

import datetime, random, math
from meerschaum.utils.misc import iterate_chunks

def register(pipe):
    return {
        'columns': {
            'datetime': 'datetime',
            'id': 'id',
        },
        'fetch': {
            'rows': 100,
            'ids': 3,
        },
    }

def fetch(pipe, chunksize=None, **kw):
    _edit_pipe = False

    sync_time = pipe.get_sync_time(round_down=False)
    now = sync_time if sync_time is not None else datetime.datetime.utcnow()
    if chunksize is None or chunksize < 1:
        chunksize = 10_000

    _dt = pipe.get_columns('datetime', error=False)
    _id = pipe.get_columns('id', error=False)
    _val = 'val'

    if _dt is None:
        _dt = 'datetime'
        pipe.columns.update({'datetime' : _dt})
        _edit_pipe = True

    if _id is None:
        _id = 'id'
        pipe.columns.update({'id' : _id})
        _edit_pipe = True

    instructions = pipe.parameters.get('fetch', {})
    _default_rows = 10_000
    _default_ids = 3
    _rows = instructions.get('rows', None)
    _ids = instructions.get('ids', None)
    if _rows is None:
        if 'fetch' not in pipe.parameters:
            pipe.parameters['fetch'] = {}
        pipe.parameters['fetch'].update({'rows' : _default_rows})
        _edit_pipe = True
        _rows = _default_rows
    if _ids is None:
        pipe.parameters['fetch'].update({'ids' : _default_ids})
        _ids = _default_ids
        _edit_pipe = True

    if _edit_pipe:
        pipe.edit()

    num_chunks = math.ceil(_rows / chunksize)

    yielded_rows = 0
    for i in range(num_chunks):
        _data = {_dt : [], _id : [], _val : []}
        for _ in range(chunksize):
            _data[_dt].append(now)
            _data[_id].append(random.randint(1, _ids))
            _data[_val].append(random.randint(1, 100))
            now += datetime.timedelta(minutes=1)
            yielded_rows += 1
            if yielded_rows >= _rows:
                break
        yield _data
