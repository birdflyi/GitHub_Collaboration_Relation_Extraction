#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/10/21 14:26
# @Author : 'Lou Zehua'
# @File   : ER_config_parser.py 

import pandas as pd

from GH_CoRE.model.ER_config import event_trigger_ERE_triples_dict


def truncate_list_to_tuple(args, length=2, default_val=None):
    if not args:
        return tuple([default_val] * length)
    if type(args) is str:
        args = [args]
    else:
        args = list(args)
    return tuple(args[i] if i < len(args) else default_val for i in range(length))


def eventType_params2repr(eventType, params: None or dict = None, delimiter='::'):
    '''
    Example 1:
        in: 'IssueCommentEvent', {"action": "created", "_on_Issue_or_PullRequest(issue_id)": "Issue"}
        out: 'IssueCommentEvent::action=created&_on_Issue_or_PullRequest(issue_id)=Issue'
    Example 2:
        in: 'IssueCommentEvent', None
        out: 'IssueCommentEvent'
    '''
    eventType_params_repr = eventType
    if params:
        eventType_params_repr = eventType + delimiter + '&'.join([str(k) + '=' + str(v) for k, v in params.items()])
    return eventType_params_repr


def get_eventType_params_from_joined_str(joined_eventType_params, delimiter='::', default_val=None):
    '''
    Example 1:
        in: 'IssueCommentEvent', '::', None
        out: ['IssueCommentEvent', None]
    Example 2:
        in: 'IssueCommentEvent::action=created', '::', None
        out: ['IssueCommentEvent', {'action': 'created'}]
    '''
    eventType, joined_params = truncate_list_to_tuple(joined_eventType_params.split(delimiter), length=2, default_val=default_val)
    params = {}
    if joined_params:
        params_item_reprs = joined_params.split('&')
        for s in params_item_reprs:
            kv = s.split("=")[:2]
            params[kv[0]] = kv[1]
    return [eventType, params]


def get_eventType_params_list_from_joined_strs(eventType_params_reprs, delimiter='::', default_val=None):
    '''
    A reverse function of get_eventType_params_reprs.
    Example 1:
        in: ['IssueCommentEvent', 'IssuesEvent::action=closed', 'IssuesEvent::action=opened'], '::', None
        out: [['IssueCommentEvent', None], ['IssuesEvent', {'action':'closed'}], ['IssuesEvent', {'action':'opened'}]]
    '''
    if any([delimiter not in s for s in eventType_params_reprs]):
        print(f"Warning: Cannot identify all actions with delimiter {delimiter}. The action will be set as {default_val}!")
    return [get_eventType_params_from_joined_str(s, delimiter=delimiter, default_val=default_val) for s in eventType_params_reprs]


def eventType_params2reprs(eventType_params, hide_unique_param=False):  # hide_unique_param = True时隐藏仅有唯一值的param条件
    '''
    Example 1:
        in: [['IssueCommentEvent', {"action": "created", "_on_Issue_or_PullRequest(issue_id)": "Issue"}]], True
        out: ['IssueCommentEvent']
    Example 2:
        in: [['IssueCommentEvent', {"action": "created", "_on_Issue_or_PullRequest(issue_id)": "Issue"}], ['IssueCommentEvent', {"action": "created", "_on_Issue_or_PullRequest(issue_id)": "PullRequest"}]], True
        out: ['IssueCommentEvent::_on_Issue_or_PullRequest(issue_id)=Issue', 'IssueCommentEvent::_on_Issue_or_PullRequest(issue_id)=PullRequest']
    Example 3:
        in: [['IssueCommentEvent', {"action": "created", "_on_Issue_or_PullRequest(issue_id)": "Issue"}], ['IssueCommentEvent', {"action": "created", "_on_Issue_or_PullRequest(issue_id)": "PullRequest"}]], False
        out: ['IssueCommentEvent::action=created&_on_Issue_or_PullRequest(issue_id)=Issue', 'IssueCommentEvent::action=created&_on_Issue_or_PullRequest(issue_id)=PullRequest']
    '''
    threshold = 1 if hide_unique_param else 0

    # eventType_params 转 dataframe
    columns = ["type"]
    for _, params in eventType_params:
        for k in params.keys():
            if k not in columns:
                columns.append(k)

    df = pd.DataFrame(columns=columns)
    for et, p in eventType_params:
        row = dict(p)
        row["type"] = et
        df.loc[len(df)] = row
    # print(df)

    # 判断需要留存的param字段
    d_eventType_keepParams = {}
    for k in list(set(df["type"])):
        d_eventType_keepParams[k] = []
    for col in columns:
        if col != "type":
            eventType_param_group_combination = df.groupby('type')[col].value_counts().reset_index(name='count')
            for k, v in d_eventType_keepParams.items():
                k_nCombination = len(eventType_param_group_combination[eventType_param_group_combination['type'] == k])
                if k_nCombination > threshold:
                    d_eventType_keepParams[k].append(col)
    # print(d_eventType_keepParams)

    # 更新eventType_params
    if hide_unique_param:
        eventType_keepParams_tuples = []
        for eventType, params in eventType_params:
            keepParams = {}
            for k, v in params.items():
                if k in d_eventType_keepParams[eventType]:
                    keepParams[k] = v
            eventType_keepParams_tuples.append((eventType, keepParams))
        # eventType_count_dict = dict(Counter([et for et, a in eventType_params]))
    else:
        eventType_keepParams_tuples = eventType_params
    eventType_params_reprs = [eventType_params2repr(eventType, params) for eventType, params in
                              eventType_keepParams_tuples]
    return eventType_params_reprs


def flatten_node_type_triples_dict(node_type_pairs_dict):
    '''
    example 1:
        in: {
            'IssuesEvent::action=opened': [
                ('Issue', 'EventAction::label=OpenedBy', 'Actor'),
                ('Issue', 'Reference::label=unknown', 'UnknownFromBodyRef')
            ]
        }
        out: [
            ('IssuesEvent::action=opened', 'Issue', 'EventAction::label=OpenedBy', 'Actor'),
            ('IssuesEvent::action=opened', 'Issue', 'Reference::label=unknown', 'UnknownFromBodyRef')
        ]
    '''
    link_triples = []
    for k, v in node_type_pairs_dict.items():
        for (s, r, t) in v:
            link_triple = (k, s, r, t)
            link_triples.append(link_triple)
    return link_triples


def match_substr__from_body(s):
    if isinstance(s, str):
        res = "FromBody" in s
    elif hasattr(s, '__iter__'):
        res = ["FromBody" in v for v in s]
    else:
        raise TypeError(f"Expect type str or iterable, but get {type(s)}!")
    return res


def record_from_body_ref_filter(record):
    '''
    example 1:
        in: pandas.core.series.Series(
            event_trigger           IssuesEvent::opened
            source_node_label                   Issue
            relation_label Reference::label=unknown
            target_node_label   UnknownFromBodyRef
            Name: 0, dtype: object)
        out: True
    '''
    matched = False
    if any(match_substr__from_body(record)):
        matched = True
    keep_flag = not matched
    return keep_flag


def event_trim_subType(node_type):
    '''
    匹配到"::str"时将此后缀移除
    example 1:
        in: IssuesEvent::opened
        out: IssuesEvent
    example 2:
        in: IssueCommentEvent
        out: IssueCommentEvent
    '''
    node_type_splits = str(node_type).split("::")
    if len(node_type_splits):
        nt_trimmed = node_type_splits[0]
    else:
        nt_trimmed = ''
    return nt_trimmed


event_triggers = sorted(list(event_trigger_ERE_triples_dict.keys()))
eventType_params = get_eventType_params_list_from_joined_strs(event_triggers)

columns_df_ref_tuples_raw = ['event_trigger', 'source_node_label', 'relation_label', 'target_node_label']
columns_df_ref_tuples = ['event_type', 'source_node_type', 'relation_type', 'target_node_type']

link_triples_raw = flatten_node_type_triples_dict(event_trigger_ERE_triples_dict)
df_ref_tuples_raw = pd.DataFrame(link_triples_raw, columns=columns_df_ref_tuples_raw)
# 图模式中将前缀相同的event_trigger看做是同一类event_type，将前缀相同node_label看作是同一类node_type，将前缀相同的relation_label看作是同一类node_type。
df_ref_tuples = df_ref_tuples_raw.applymap(event_trim_subType)
df_ref_tuples.columns = columns_df_ref_tuples


if __name__ == '__main__':
    # from script.model.ER_config import event_trigger_ERE_triples_dict
    from GH_CoRE.utils.prepare_sql import get_params_condition, format_sql

    test_eventType_params_reprs = eventType_params2reprs([['IssueCommentEvent', {"action": "created", "_on_Issue_or_PullRequest(issue_id)": "Issue"}], ['IssueCommentEvent', {"action": "created", "_on_Issue_or_PullRequest(issue_id)": "PullRequest"}], ['a_event', {"action": "test"}]], False)
    print(test_eventType_params_reprs)

    print(event_triggers)
    print(eventType_params)
    eventType_reprs_abbr = eventType_params2reprs(eventType_params, hide_unique_param=True)
    print(eventType_reprs_abbr)
    for eventType, params in eventType_params:
        params_condition_dict = dict({"platform": 'GitHub', "type": eventType}, **params)
        sql_params = {
            "params_condition": get_params_condition(params_condition_dict),
            # "limit": 10
        }
        sql = format_sql(sql_params)
        print(sql)

    entity_label_set = set(list(df_ref_tuples_raw[["source_node_label", "target_node_label"]].values.flatten()))
    print(len(entity_label_set), entity_label_set)

    IGNORE_BODY_CROSS_REFERENCE = False  # 当设置为True时，图模式中不显示BODY_CROSS_REFERENCE有关的连边。
    if IGNORE_BODY_CROSS_REFERENCE:
        df_ref_tuples = df_ref_tuples[df_ref_tuples_raw.apply(record_from_body_ref_filter, axis=1)]  # filter the body reference
    print(df_ref_tuples)

    node_type_set = set(df_ref_tuples["source_node_type"]).union(set(df_ref_tuples["target_node_type"]))
    print(len(node_type_set), node_type_set)
