#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2023/4/19 21:14
# @Author : 'Lou Zehua'
# @File   : query_OSDB_github_log.py

import os

import pandas as pd

from GH_CoRE.data_dict_settings import columns_simple
from GH_CoRE.utils.conndb import ConnDB


def get_repo_name_fileformat(repo_name: str):
    return repo_name.replace('/', '_')


def get_repo_year_filename(repo_name_fileformat: str, year):
    return f"{repo_name_fileformat}_{str(year)}.csv"


def query_repo_log_each_year_to_csv_dir(repo_names, columns, save_dir, sql_param=None, update_exist_data=False):
    conndb = ConnDB()
    columns_str = ', '.join(columns)
    sql_param = sql_param or {}
    sql_param = dict(sql_param)
    table = sql_param.get("table", "opensource.events")
    start_end_year = sql_param.get("start_end_year", [2022, 2023])
    start_year = start_end_year[0]
    try:
        end_year = start_end_year[1]
    except IndexError:
        end_year = start_year + 1
    get_year_constraint = lambda x, y=None: f"created_at BETWEEN '{str(x)}-01-01 00:00:00' AND '{str(y or (x + 1))}-01-01 00:00:00'"

    # query and save
    for year in range(start_year, end_year):
        sql_ref_repo_pattern = f'''
        SELECT {{columns}} FROM {table} WHERE platform='GitHub' AND {get_year_constraint(year)} AND repo_name='{{repo_name}}';
        '''
        for repo_name in repo_names:
            sql_ref_repo = sql_ref_repo_pattern.format(**{"columns": columns_str, "repo_name": repo_name})
            # print(sql_ref_repo)

            repo_name_fileformat = get_repo_name_fileformat(repo_name)
            filename = get_repo_year_filename(repo_name_fileformat, year)
            save_path = os.path.join(save_dir, filename)

            if update_exist_data or not os.path.exists(save_path):
                conndb.sql = sql_ref_repo
                try:
                    conndb.execute()
                    conndb.rs.to_csv(save_path)
                except BaseException as e:
                    print(f"{filename} is skipped due to an unexpected error: {e.__class__.__name__}!")
                    return
                print(f"{filename} saved!")
            else:
                print(f"{filename} exists!")
    print("Query Completed!")
    return


if __name__ == '__main__':
    from etc import filePathConf

    # 1. 按repo_name分散存储到每一个csv文件中
    UPDATE_EXIST_DATA = False  # UPDATE SAVED RESULTS FLAG

    # 1.1 repo reference features as columns of sql
    columns = columns_simple

    # 1.2 get repo_names as condition of sql
    # repo_names = ['sqlite/sqlite', 'MariaDB/server', 'mongodb/mongo', 'redis/redis', 'elastic/elasticsearch', 'influxdata/influxdb', 'ClickHouse/ClickHouse', 'apache/hbase']
    df_OSDB_githubprj = pd.read_csv(os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR],
                                                 "dbfeatfusion_records_202306_automerged_manulabeled_with_repoid.csv"),
                                    header='infer', index_col=None)
    df_OSDB_githubprj = df_OSDB_githubprj[pd.notna(df_OSDB_githubprj["github_repo_id"])]  # filter github_repo_id must exist

    repo_names = list(df_OSDB_githubprj["github_repo_link"].values)

    # # test cases
    # tst_repo = ['sqlite/sqlite', 'MariaDB/server', 'mongodb/mongo', 'redis/redis', 'elastic/elasticsearch',
    #             'influxdata/influxdb', 'ClickHouse/ClickHouse', 'apache/hbase']
    # assert (all([r in repo_names for r in tst_repo]))
    # repo_names = tst_repo

    # 1.3 query and save
    save_dir = os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR], "repos")
    sql_param = {
        "table": "opensource.events",
        "start_end_year": [2022, 2023],
    }
    query_repo_log_each_year_to_csv_dir(repo_names, columns, save_dir, sql_param, update_exist_data=UPDATE_EXIST_DATA)
