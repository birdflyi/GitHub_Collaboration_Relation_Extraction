#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2023/4/19 21:14
# @Author : 'Lou Zehua'
# @File   : query_OSDB_github_log.py

import os
import sys

if '__file__' not in globals():
    # !pip install ipynbname  # Remove comment symbols to solve the ModuleNotFoundError
    import ipynbname

    nb_path = ipynbname.path()
    __file__ = str(nb_path)
cur_dir = os.path.dirname(__file__)
pkg_rootdir = cur_dir  # os.path.dirname()向上一级，注意要对应工程root路径
if pkg_rootdir not in sys.path:  # 解决ipynb引用上层路径中的模块时的ModuleNotFoundError问题
    sys.path.append(pkg_rootdir)
    print('-- Add root directory "{}" to system path.'.format(pkg_rootdir))

import numpy as np
import pandas as pd

from etc import filePathConf
from script import columns_simple, body_columns_dict, event_columns_dict, re_ref_patterns
from script.body_content_preprocessing import read_csvs
from script.identify_reference import find_substrs_in_df_repos_ref_type_local_msg, dump_to_pickle, load_pickle
from script.query_OSDB_github_log import query_repo_log_each_year_to_csv_dir


if __name__ == '__main__':
    # Download sample data
    repo_names = ["elastic/elasticsearch"]
    dbms_repos_raw_content_dir = os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR], 'repos')
    sql_param = {
        "table": "opensource.events",
        "start_end_year": [2023, 2024],
    }
    query_repo_log_each_year_to_csv_dir(repo_names, columns=columns_simple, save_dir=dbms_repos_raw_content_dir,
                                        sql_param=sql_param)

    # Named Entity Recognition
    df_repos_dict = read_csvs(dbms_repos_raw_content_dir)
    local_msg_dict = df_repos_dict
    repo_keys = list(df_repos_dict.keys())[:1]
    use_msg_columns = body_columns_dict['local_descriptions']
    ref_substrs_pkl_save_path = os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR],
                                             "repos_ref_type_local_msg_substrs_dict.pkl")
    if not os.path.exists(ref_substrs_pkl_save_path):
        df_repos_ref_type_local_msg_substrs_dict = find_substrs_in_df_repos_ref_type_local_msg(
            local_msg_dict, repo_keys, re_ref_patterns, use_msg_columns, record_key='id')
        dump_to_pickle(df_repos_ref_type_local_msg_substrs_dict, ref_substrs_pkl_save_path, update=False)
    else:
        df_repos_ref_type_local_msg_substrs_dict = load_pickle(ref_substrs_pkl_save_path)
    pd.set_option('display.max_columns', None)
    df = df_repos_ref_type_local_msg_substrs_dict[repo_keys[0]][list(re_ref_patterns.keys())[0]]
    print(df[event_columns_dict['basic'] + use_msg_columns].head())

    # Entity Search
    # todo
