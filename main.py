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
import pandas as pd

from functools import partial

from etc import filePathConf
from GH_CoRE.data_dict_settings import columns_simple
from GH_CoRE.working_flow.body_content_preprocessing import read_csvs, dedup_content
from GH_CoRE.model.Relation_extraction import get_obj_collaboration_tuples_from_record, get_df_collaboration, \
    save_GitHub_Collaboration_Network
from GH_CoRE.working_flow.query_OSDB_github_log import query_repo_log_each_year_to_csv_dir, get_repo_name_fileformat, \
    get_repo_year_filename
from GH_CoRE.utils.cache import QueryCache
from GH_CoRE.utils.logUtils import setup_logging


def query_OSDB_github_log_from_dbserver(key_feats_path=None, save_dir=None, update_exist_data=False):
    # 1. 按repo_name分散存储到每一个csv文件中
    UPDATE_EXIST_DATA = update_exist_data  # UPDATE SAVED RESULTS FLAG
    # 1.1 repo reference features as columns of sql
    columns = columns_simple
    # 1.2 get repo_names as condition of sql
    # repo_names = ['sqlite/sqlite', 'MariaDB/server', 'mongodb/mongo', 'redis/redis', 'elastic/elasticsearch', 'influxdata/influxdb', 'ClickHouse/ClickHouse', 'apache/hbase']
    key_feats_path = key_feats_path or os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR],
                                                    "dbfeatfusion_records_202306_automerged_manulabeled_with_repoid.csv")
    df_OSDB_github_key_feats = pd.read_csv(key_feats_path, header='infer', index_col=None)
    df_OSDB_github_key_feats = df_OSDB_github_key_feats[
        pd.notna(df_OSDB_github_key_feats["github_repo_id"])]  # filter github_repo_id must exist
    repo_names = list(df_OSDB_github_key_feats["github_repo_link"].values)
    # 1.3 query and save
    save_dir = save_dir or os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR], "repos")
    sql_param = {
        "table": "opensource.gh_events",
        "start_end_year": [2022, 2023],
    }
    query_repo_log_each_year_to_csv_dir(repo_names, columns, save_dir, sql_param, update_exist_data=UPDATE_EXIST_DATA)
    return


def process_body_content(raw_content_dir=None, processed_content_dir=None, filenames=None, dedup_content_overwrite=False):
    # reduce_redundancy
    # 读入csv，去除数据库存储时额外复制的重复issue信息
    dbms_repos_dir = raw_content_dir or os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR], 'repos')
    df_dbms_repos_raw_dict = read_csvs(dbms_repos_dir, filenames=filenames, index_col=0)
    # print("len(df_dbms_repos_raw_dict): ", len(df_dbms_repos_raw_dict))
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


def collaboration_relation_extraction(repo_keys, df_dbms_repos_dict, save_dir, repo_key_skip_to_loc=None,
                                      last_stop_index=None, limit=None, update_exists=True, add_mode_if_exists=True,
                                      cache_max_size=200):
    """
    :param repo_keys: filenames right stripped by suffix `.csv`
    :param df_dbms_repos_dict: key: repo_keys, value: dataframe of dbms repos event logs
    :param save_dir: save the results for each `repo_key` in repo_keys into this directory
    :param repo_key_skip_to_loc: skip the indexes of repo keys smaller than repo_key_skip_to_loc in the order of df_dbms_repos_dict.keys()
    :param last_stop_index: set last_stop_index = -1 or None(by default) if skip nothing
    :param limit: set limit = -1 or None(by default) if no limit
    :param update_exists: only process repo_keys not exists old result when update_exists=False
    :param add_mode_if_exists: only takes effect when parameter update_exists=True
    :param cache_max_size: int type, set cache_max_size=-1 if you donot want to use any cache
    :return: None
    """
    repo_key_skip_to_loc = repo_key_skip_to_loc if repo_key_skip_to_loc is not None else 0
    last_stop_index = last_stop_index if last_stop_index is not None else -1  # set last_stop_index = -1 if skip nothing
    # last_stop_index + 1,  this last_stop_index is the index of rows where the raw log file `id` column matches the
    # `event_id` column in the file result log file.
    rec_add_mode_skip_to_loc = last_stop_index + 1

    limit = limit if limit is not None else -1
    I_REPO_KEY = 0
    I_REPO_LOC = 1
    I_RECORD_LOC = 2
    process_checkpoint = ['', 0, 0]
    cache = QueryCache(max_size=cache_max_size) if cache_max_size > 0 else None
    cache.match_func = partial(QueryCache.d_match_func,
                               **{"feat_keys": ["link_pattern_type", "link_text", "rec_repo_id"]})
    try:
        for i, repo_key in enumerate(repo_keys):
            process_checkpoint[I_REPO_KEY] = repo_key
            process_checkpoint[I_REPO_LOC] = i
            if i < repo_key_skip_to_loc:
                continue
            df_repo = df_dbms_repos_dict[repo_key]
            save_path = os.path.join(save_dir, f'{repo_key}.csv')
            if os.path.exists(save_path) and not update_exists:
                continue

            for index, rec in df_repo.iterrows():
                process_checkpoint[I_RECORD_LOC] = index
                if limit > 0:
                    if index >= limit:
                        logger.info(
                            f"Processing progress: {repo_key}@{i}: [{rec_add_mode_skip_to_loc}: {index}]. Batch task completed!")
                        break
                if index < rec_add_mode_skip_to_loc:
                    continue
                obj_collaboration_tuple_list, cache = get_obj_collaboration_tuples_from_record(rec, cache=cache)
                df_collaboration = get_df_collaboration(obj_collaboration_tuple_list, extend_field=True)
                save_GitHub_Collaboration_Network(df_collaboration, save_path=save_path, add_mode_if_exists=add_mode_if_exists)
            logger.info(f"Processing progress: {repo_key}@{i}#{process_checkpoint[I_RECORD_LOC]}: task completed!")
            rec_add_mode_skip_to_loc = 0
        logger.info(f"Processing progress: all task completed!")
    except BaseException as e:
        logger.info(
            f"Processing progress: {process_checkpoint[I_REPO_KEY]}@{process_checkpoint[I_REPO_LOC]}#{process_checkpoint[I_RECORD_LOC]}. "
            f"The process stopped due to an exception!")
        tb_lines = traceback.format_exception(e.__class__, e, e.__traceback__)
        logger.error(''.join(tb_lines))
    return


if __name__ == '__main__':
    setup_logging(base_dir=pkg_rootdir)
    logger = logging.getLogger(__name__)

    # Download sample data
    year = 2023
    repo_names = ["apache/lucene-solr", "TuGraph-family/tugraph-db", "facebook/rocksdb", "cockroachdb/cockroach"][0:1]

    dbms_repos_raw_content_dir = os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR], 'repos')
    if repo_names:
        sql_param = {
            "table": "opensource.events",
            "start_end_year": [year, year + 1],
        }
        query_repo_log_each_year_to_csv_dir(repo_names, columns=columns_simple, save_dir=dbms_repos_raw_content_dir,
                                            sql_param=sql_param)
    else:
        query_OSDB_github_log_from_dbserver(key_feats_path=dbms_repos_raw_content_dir, save_dir=dbms_repos_raw_content_dir)

    filenames_exists = os.listdir(dbms_repos_raw_content_dir)
    if repo_names:
        repo_names_fileformat = list(map(get_repo_name_fileformat, repo_names))
        filenames = [get_repo_year_filename(s, year) for s in repo_names_fileformat]
        filenames = [filename for filename in filenames if filename in filenames_exists]
    else:
        filenames = filenames_exists

    # Preprocess body content
    dbms_repos_dedup_content_dir = os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR], 'repos_dedup_content')
    process_body_content(raw_content_dir=dbms_repos_raw_content_dir, processed_content_dir=dbms_repos_dedup_content_dir, filenames=filenames)
    df_dbms_repos_dict = read_csvs(dbms_repos_dedup_content_dir, filenames=filenames, index_col=0)
    repo_keys = list(df_dbms_repos_dict.keys())

    # Collaboration Relation extraction
    relation_extraction_save_dir = os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR],
                                                "GitHub_Collaboration_Network_repos")
    collaboration_relation_extraction(repo_keys, df_dbms_repos_dict, relation_extraction_save_dir, update_exists=True,
                                      add_mode_if_exists=True)

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
