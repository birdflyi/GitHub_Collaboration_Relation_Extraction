#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/10/25 7:01
# @Author : 'Lou Zehua'
# @File   : Entity_recognition.py 

import pandas as pd

from GH_CoRE.data_dict_settings import re_ref_patterns
from GH_CoRE.working_flow.identify_reference import get_df_local_msg_regexed_dict, regex_df


def merge_links_in_records(record, use_msg_columns):
    body_regexed_links = []
    for c in use_msg_columns:
        tmp_links = record[c]
        if isinstance(tmp_links, list):
            body_regexed_links += tmp_links
    return body_regexed_links


# Entity Recognition
def get_df_bodyRegLinks_eachLinkPatType(df_local_msg, use_msg_columns=None):
    use_msg_columns = use_msg_columns or ['issue_title', 'body', 'push_commits.message', 'release_body']
    df_local_msg_regexed_dict = get_df_local_msg_regexed_dict(df_local_msg, use_msg_columns=use_msg_columns)
    df_bodyRegLinks_eachLinkPatType = pd.DataFrame()
    for link_pattern_type, df_local_msg_regexed in df_local_msg_regexed_dict.items():
        temp_ser = pd.Series([], dtype=object)
        if len(df_local_msg_regexed):
            # 可以合并的原因是use_msg_columns中的各列内容在各自对应的event type分别出现，而不会同时出现
            temp_ser = df_local_msg_regexed[use_msg_columns].apply(lambda rec: merge_links_in_records(rec, use_msg_columns), axis=1)
        temp_df = pd.Series(temp_ser, name=link_pattern_type).to_frame()
        df_bodyRegLinks_eachLinkPatType = df_bodyRegLinks_eachLinkPatType.merge(temp_df, left_index=True, right_index=True, how='outer')
    return df_bodyRegLinks_eachLinkPatType


if __name__ == '__main__':
    from GH_CoRE.model.tst_case import df_tst

    df_regexed = regex_df(df_tst.loc[1].to_frame().T[['id', 'body']], ['body'], re_ref_patterns["Issue_PR"][4], use_data_conf=1)
    print(df_regexed)
    print(get_df_local_msg_regexed_dict(df_regexed))
    print(get_df_bodyRegLinks_eachLinkPatType(df_tst))
