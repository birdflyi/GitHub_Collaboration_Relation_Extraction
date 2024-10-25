#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/10/21 14:37
# @Author : 'Lou Zehua'
# @File   : prepare_sql.py

import re


def get_params_condition(d_params=None, lstrip_and_connector=True):
    s = ""
    and_connector = " and "
    if d_params:
        for k, v in d_params.items():
            s += f"{and_connector}{k}='{v}'"
    if lstrip_and_connector and s.startswith(and_connector):
        s = s[len(and_connector):]
    return s


def format_sql(sql_params):
    sql_pattern = """SELECT {columns} 
    FROM {table} 
    {where} 
    {group_by} 
    {having} 
    {order_by} 
    {limit};"""

    default_sql_params = {
        "columns": sql_params.get('columns', '*'),
        "table": sql_params.get('table', 'opensource.events'),
        "where": f"WHERE {sql_params['where']}" if sql_params.get(
            'where') else "WHERE {params_condition}".format(**sql_params),
        "group_by": f"GROUP BY {sql_params['group_by']}" if sql_params.get('group_by') else '',
        "having": f"HAVING {sql_params['having']}" if sql_params.get('having') else '',
        "order_by": f"ORDER BY {sql_params['order_gy']}" if sql_params.get('order_by') else '',
        "limit": f"LIMIT {sql_params['limit']}" if sql_params.get('limit') else ''
    }

    sql = sql_pattern.format(**default_sql_params)
    sql = re.sub('\n', '', sql)
    sql = re.sub(' +', ' ', sql)
    sql = re.sub(' +;', ';', sql)
    return sql


if __name__ == '__main__':
    eventType_params = [['CommitCommentEvent', {'action': 'added'}], ['CreateEvent', {'action': 'added', 'create_ref_type': 'branch'}]]
    params_condition_dict = dict({"platform": 'GitHub', "type": eventType_params[0][0]}, **eventType_params[0][1])
    print(params_condition_dict)
    sql_params = {
        "params_condition": get_params_condition(params_condition_dict),
        "limit": 10
    }
    print(sql_params)
    sql = format_sql(sql_params)
    print(sql)
