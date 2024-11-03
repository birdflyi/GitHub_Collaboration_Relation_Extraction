#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2023/4/19 21:14
# @Author : 'Lou Zehua'
# @File   : main.py

import os
import sys
import traceback

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

import logging

from etc import filePathConf
from script import columns_simple, columns_full
from script.body_content_preprocessing import read_csvs, dedup_content
from script.model.Relation_extraction import get_obj_collaboration_tuples_from_record, get_df_collaboration, \
    save_GitHub_Collaboration_Network
from script.query_OSDB_github_log import query_repo_log_each_year_to_csv_dir, get_repo_name_fileformat, \
    get_repo_year_filename
from utils.logUtils.loadLogConfig import setup_logging


def process_body_content(raw_content_dir=None, processed_content_dir=None, dedup_content_overwrite=False):
    # reduce_redundancy
    # 读入csv，去除数据库存储时额外复制的重复issue信息
    dbms_repos_dir = raw_content_dir or os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR], 'repos')
    df_dbms_repos_raw_dict = read_csvs(dbms_repos_dir, index_col=0)
    # print(len(df_dbms_repos_raw_dict))
    DEDUP_CONTENT_OVERWRITE = dedup_content_overwrite  # UPDATE SAVED RESULTS FLAG
    dbms_repos_dedup_content_dir = processed_content_dir or os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR], 'repos_dedup_content')
    for repo_key, df_dbms_repo in df_dbms_repos_raw_dict.items():
        save_path = os.path.join(dbms_repos_dedup_content_dir, "{repo_key}.csv".format(**{"repo_key": repo_key}))
        if DEDUP_CONTENT_OVERWRITE or not os.path.exists(save_path):
            dedup_content(df_dbms_repo).to_csv(save_path)
    if not DEDUP_CONTENT_OVERWRITE:
        print('skip exist dedup_content...')
    print('dedup_content done!')
    return


if __name__ == '__main__':
    setup_logging()
    logger = logging.getLogger(__name__)

    # Download sample data
    repo_names = ["facebook/rocksdb", "TuGraph-family/tugraph-db"][0:1]
    dbms_repos_raw_content_dir = os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR], 'repos')
    year = 2023
    sql_param = {
        "table": "opensource.events",
        "start_end_year": [year, year + 1],
    }
    query_repo_log_each_year_to_csv_dir(repo_names, columns=columns_simple, save_dir=dbms_repos_raw_content_dir,
                                        sql_param=sql_param)

    # Preprocess body content
    dbms_repos_dedup_content_dir = os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR], 'repos_dedup_content')
    process_body_content(raw_content_dir=dbms_repos_raw_content_dir, processed_content_dir=dbms_repos_dedup_content_dir)

    # Relation extraction
    repo_names_fileformat = list(map(get_repo_name_fileformat, repo_names))
    filenames = [get_repo_year_filename(s, year) for s in repo_names_fileformat]
    df_dbms_repos_dict = read_csvs(dbms_repos_dedup_content_dir, filenames=filenames, index_col=0)
    repo_keys = list(df_dbms_repos_dict.keys())

    repo_key_skip_to_loc = 0
    last_stop_index = -1  # set last_stop_index = -1 if skip nothing
    # last_stop_index + 1,  this last_stop_index is the index of rows where the raw log file `id` column matches the
    # `event`_id column in the file result log file.
    rec_add_mode_skip_to_loc = last_stop_index + 1

    # limit = 1000
    limit = -1
    I_REPO_KEY = 0
    I_REPO_LOC = 1
    I_RECORD_LOC = 2
    process_checkpoint = ['', 0, 0]
    try:
        for i, repo_key in enumerate(repo_keys):
            process_checkpoint[I_REPO_KEY] = repo_key
            process_checkpoint[I_REPO_LOC] = i
            if i < repo_key_skip_to_loc:
                continue
            df_repo = df_dbms_repos_dict[repo_key]
            save_path = os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR], f'GitHub_Collaboration_Network_repos/{repo_key}.csv')
            for index, rec in df_repo.iterrows():
                process_checkpoint[I_RECORD_LOC] = index
                if limit > 0:
                    if index >= limit:
                        logger.info(f"Processing progress: {repo_key}@{i}: [{rec_add_mode_skip_to_loc}: {index}]. Batch task completed!")
                        break
                if index < rec_add_mode_skip_to_loc:
                    continue
                obj_collaboration_tuple_list = get_obj_collaboration_tuples_from_record(rec)
                df_collaboration = get_df_collaboration(obj_collaboration_tuple_list, extend_field=True)
                save_GitHub_Collaboration_Network(df_collaboration, save_path=save_path, add_mode_if_exists=True)
            logger.info(f"Processing progress: {repo_key}@{i}#{process_checkpoint[I_RECORD_LOC]}: task completed!")
            rec_add_mode_skip_to_loc = 0
        logger.info(f"Processing progress: all task completed!")
    except BaseException as e:
        logger.info(f"Processing progress: {process_checkpoint[I_REPO_KEY]}@{process_checkpoint[I_REPO_LOC]}#{process_checkpoint[I_RECORD_LOC]}. "
                    f"The process stopped due to an exception!")
        tb_lines = traceback.format_exception(e.__class__, e, e.__traceback__)
        logger.error(''.join(tb_lines))

    # # Just for test
    # import pandas as pd
    #
    # df = pd.read_csv(debug_records_path, index_col=None, header=None)
    # df.columns = columns_full
    # for index, rec in df.iterrows():
    #     if index < 6:
    #         continue
    #     obj_collaboration_tuple_list = get_obj_collaboration_tuples_from_record(rec)
    #     df_collaboration = get_df_collaboration(obj_collaboration_tuple_list, extend_field=True)
    #     pd.set_option('display.max_columns', None)
    #     print(df_collaboration)
