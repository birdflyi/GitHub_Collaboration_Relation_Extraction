#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/10/23 1:41
# @Author : 'Lou Zehua'
# @File   : Attribute_getter.py

# Query GitHub API
import os

import pandas as pd

from GH_CoRE.utils.conndb import ConnDB
from GH_CoRE.utils.prepare_sql import get_params_condition, format_sql
from GH_CoRE.utils.request_api import RequestGitHubAPI, GitHubGraphQLAPI

USE_LOC_ACTOR_REPO_TABLE = False
UPDATE_LOC_ACTOR_REPO_TABLE = False


# 1. local cache
def prepare_loc_actor_repo_table():
    df_Actor = pd.DataFrame()
    df_Repo = pd.DataFrame()
    if USE_LOC_ACTOR_REPO_TABLE:
        path_Actor = "data/global_data/Actor.csv"
        path_Repo = "data/global_data/Repo.csv"
        conndb = ConnDB()
        if UPDATE_LOC_ACTOR_REPO_TABLE or not os.path.exists(path_Actor):
            # 更新Actor.csv
            conndb.sql = """SELECT DISTINCT(actor_id) AS actor_id, anyHeavy(actor_login) AS actor_login FROM opensource.events WHERE platform='GitHub' GROUP BY actor_id ORDER BY actor_id;"""
            try:
                conndb.execute()
                conndb.rs.to_csv(path_Actor, encoding='utf-8')
            except BaseException as e:
                print(f"{path_Actor} is not updated due to an unexpected error: {e.__class__.__name__}!")
            df_Actor = pd.DataFrame() if conndb.rs is None else conndb.rs
        else:
            df_Actor = pd.read_csv(path_Actor, encoding='utf-8')

        if UPDATE_LOC_ACTOR_REPO_TABLE or not os.path.exists(path_Repo):
            # 更新Repo.csv created_at只取一年的，避免超出内存上限的查询错误
            conndb.sql = """SELECT repo_id, repo_name FROM opensource.events WHERE platform='GitHub' AND created_at BETWEEN '2023-01-01 00:00:00' AND '2024-01-01 00:00:00' GROUP BY repo_id, repo_name;"""
            try:
                conndb.execute()
                conndb.rs.to_csv(path_Repo, encoding='utf-8')
            except BaseException as e:
                print(f"{path_Repo} is not updated due to an unexpected error: {e.__class__.__name__}!")
            df_Repo = pd.DataFrame() if conndb.rs is None else conndb.rs
        else:
            df_Repo = pd.read_csv(path_Repo, encoding='utf-8')
    return df_Actor, df_Repo


df_Actor, df_Repo = prepare_loc_actor_repo_table()


# 2. query entity attributes from DataBase
def _get_field_from_db(field, where_param, ret='any', dataframe_format=False, **kwargs):
    if "platform" not in where_param.keys():
        where_param = dict({"platform": 'GitHub'}, **where_param)
    where_param_trimed = {k: v for k, v in where_param.items() if v is not None}
    params_condition = get_params_condition(where_param_trimed)
    sql_params = dict(kwargs) if kwargs else {}
    sql_params["columns"] = field
    sql_params["table"] = kwargs.get('table', 'opensource.events')
    sql_params["params_condition"] = params_condition
    if ret == 'any':
        sql_params["limit"] = 1
    sql = format_sql(sql_params)

    conndb = ConnDB()
    conndb.sql = sql
    try:
        conndb.execute()
    except BaseException as e:
        print(f"An unexpected error occurred: {e.__class__.__name__}! The query sql: {sql}.")
    df_rs = pd.DataFrame() if conndb.rs is None else conndb.rs
    if not len(df_rs):
        return None if not dataframe_format else pd.DataFrame()

    if ret in ['first', 'any']:
        result = df_rs.iloc[0]
    elif ret == 'last':
        result = df_rs.iloc[-1]
    elif ret == 'all':
        result = df_rs
    else:
        raise ValueError("ret must be in ['first', 'any', 'last', 'all']!")
    if not dataframe_format:
        result = result[df_rs.columns[0]]
        if ret != 'all' and type(result) == list:
            result = result[0]
    return result


def get_actor_id_by_actor_login(actor_login, use_loc_table=USE_LOC_ACTOR_REPO_TABLE):
    if actor_login is None:
        return None

    actor_id = None
    query_flag = False
    if use_loc_table:
        try:
            actor_id = df_Actor.loc[df_Actor['actor_login'] == actor_login, 'actor_id'].values[0]
        except:
            print(f"Can not find {actor_login} in Actor.csv. Try to connect to clickhouse...")
            query_flag = True
    else:
        query_flag = True

    if query_flag:
        actor_id = _get_field_from_db('actor_id', {'actor_login': actor_login})
        if not actor_id:
            actor_id = __get_actor_id_by_actor_login(actor_login)
    return actor_id


def get_actor_login_by_actor_id(actor_id, use_loc_table=USE_LOC_ACTOR_REPO_TABLE):
    if actor_id is None:
        return None

    actor_login = None
    query_flag = False
    if use_loc_table:
        try:
            actor_login = df_Actor.loc[df_Actor['actor_id'] == actor_id, 'actor_login'].values[0]
        except:
            print(f"Can not find {str(actor_id)} in Actor.csv. Try to connect to clickhouse...")
            query_flag = True
    else:
        query_flag = True

    if query_flag:
        actor_login = _get_field_from_db('actor_login', {'actor_id': actor_id})
        if not actor_login:
            actor_login = __get_actor_login_by_actor_id(actor_id)
    return actor_login


def get_repo_id_by_repo_full_name(repo_full_name, use_loc_table=USE_LOC_ACTOR_REPO_TABLE):
    if repo_full_name is None:
        return None

    repo_id = None
    query_flag = False
    if use_loc_table:
        try:
            repo_id = df_Repo.loc[df_Repo['repo_name'] == repo_full_name, 'repo_id'].values[0]
        except:
            print(f"Can not find {repo_full_name} in Repo.csv. Try to connect to clickhouse...")
            query_flag = True
    else:
        query_flag = True

    if query_flag:
        repo_id = _get_field_from_db('repo_id', {'repo_name': repo_full_name})
        if not repo_id:
            repo_id = __get_repo_id_by_repo_full_name(repo_full_name)
    return repo_id


def get_repo_name_by_repo_id(repo_id, use_loc_table=USE_LOC_ACTOR_REPO_TABLE):
    if repo_id is None:
        return None

    repo_name = None
    query_flag = False
    if use_loc_table:
        try:
            repo_name = df_Repo.loc[df_Repo['repo_id'] == repo_id, 'repo_name'].values[0]
        except:
            print(f"Can not find {str(repo_id)} in Repo.csv. Try to connect to clickhouse...")
            query_flag = True
    else:
        query_flag = True

    if query_flag:
        repo_name = _get_field_from_db('repo_name', {'repo_id': repo_id})
        if not repo_name:
            repo_name = __get_repo_full_name_by_repo_id(repo_id)
    return repo_name


# 3. query entity attributes from GitHub API

def __get_actor_id_by_actor_login(actor_login):
    actor_id = None
    requestGitHubAPI = RequestGitHubAPI(url_pat_mode="name")
    url = requestGitHubAPI.get_url("actor", params={"actor_login": actor_login})
    response = requestGitHubAPI.request(url)
    if response is not None:
        data = response.json()
        actor_id = data.get("id", None)
    else:
        print("Empty data.")
    return actor_id


def __get_actor_login_by_actor_id(actor_id):
    actor_login = None
    requestGitHubAPI = RequestGitHubAPI(url_pat_mode="id")
    url = requestGitHubAPI.get_url("actor", params={"actor_id": actor_id})
    response = requestGitHubAPI.request(url)
    if response is not None:
        data = response.json()
        actor_login = data.get("login", None)
    else:
        print("Empty data.")
    return actor_login


def __get_repo_id_by_repo_full_name(repo_name):
    repo_id = None
    requestGitHubAPI = RequestGitHubAPI(url_pat_mode="name")
    url = requestGitHubAPI.get_url("repo", params={"owner": repo_name.split("/")[0], "repo": repo_name.split("/")[-1]})
    response = requestGitHubAPI.request(url)
    if response is not None:
        data = response.json()
        repo_id = data.get("id", None)
    else:
        print("Empty data.")
    return repo_id


def __get_repo_full_name_by_repo_id(repo_id):
    repo_name = None
    requestGitHubAPI = RequestGitHubAPI(url_pat_mode="id")
    url = requestGitHubAPI.get_url("repo", params={"repo_id": repo_id})
    response = requestGitHubAPI.request(url)
    if response is not None:
        data = response.json()
        repo_name = data.get("full_name", None)
    else:
        print("Empty data.")
    return repo_name


def __get_github_userinfo_from_email(email):
    usersinfo = None

    requestGitHubAPI = RequestGitHubAPI()
    url = f"https://api.github.com/search/users?q={email}"
    response = requestGitHubAPI.request(url)
    if response is not None:
        data = response.json()
        users = data['items']
        if users:
            usersinfo = users[0]
    else:
        print("Empty data.")
    return usersinfo


def __get_issue_type(repo_id, issue_number):
    requestGitHubAPI = RequestGitHubAPI(url_pat_mode="id")
    url = f"https://api.github.com/repositories/{repo_id}/issues/{issue_number}"
    response = requestGitHubAPI.request(url)
    issue_type = None
    if response is not None:
        issue_data = response.json()
        if issue_data.get('pull_request', None) is None:
            issue_type = 'Issue'
        else:
            issue_type = 'PullRequest'
    else:
        print("Empty data.")
    return issue_type


# https://github.com/X-lab2017/open-digger/commit/e5b25fba712a6d675fbf8328ef44ae0e1a8e377e
# 1 parent: https://github.com/X-lab2017/open-digger/commit/f9f3c6eddd0e9bfbefef54a7f28c65c6914ad566
# repo_full_name = 'X-lab2017/open-digger'  # 'owner/repo'
# commit_sha = 'e5b25fba712a6d675fbf8328ef44ae0e1a8e377e'
# url = f'https://api.github.com/repos/{repo_full_name}/git/commits/{commit_sha}'

# __get_PR_commits_sha示例：getJson(https://api.github.com/repos/X-lab2017/open-digger/pulls/1292/commits).[i].sha
def __get_PR_commits_sha(issue_number, repo_id):
    url_params = {
        "repo_id": repo_id,
        "issue_number": issue_number
    }
    requestGitHubAPI = RequestGitHubAPI(url_pat_mode='id')
    url = requestGitHubAPI.get_url(url_type="repo_ext", ext_pat='/pulls/{issue_number}/commits', params=url_params)
    # print(url)
    response = requestGitHubAPI.request(url)
    commit_sha_list = []
    if response is not None:
        data = response.json()
        commit_sha_list = [commit['sha'] for commit in data]
        # print(commit_sha_list)
    else:
        print("Empty data.")
    return commit_sha_list


def __get_PR_commits_sha_by_issue_exid(_issue_exid):
    params = {
        'repo_id': _issue_exid.split('#')[0],
        'issue_number': _issue_exid.split('#')[1],
    }
    return __get_PR_commits_sha(**params)


def __get_commit_parents_sha(commit_sha, repo_id=None, repo_full_name=None):
    url_pat_mode = None
    if not (repo_id or repo_full_name):
        raise ValueError("repo_id and repo_full_name cannot be None at the same time.")
    else:
        if repo_id:
            url_pat_mode = 'id'
        else:
            url_pat_mode = 'name'

    url_params = {
        "owner": repo_full_name.split('/')[0] if repo_full_name else None,
        "repo": repo_full_name.split('/')[1] if repo_full_name else None,
        "repo_id": repo_id if repo_id else None,
        "commit_sha": commit_sha
    }
    requestGitHubAPI = RequestGitHubAPI(url_pat_mode=url_pat_mode)
    url = requestGitHubAPI.get_url(url_type="commit", params=url_params)
    # print(url)
    response = requestGitHubAPI.request(url)
    parent_sha_list = []
    if response is not None:
        data = response.json()
        parent_sha_list = [commit['sha'] for commit in data['parents']]
        # print(parent_sha_list)
    else:
        print("Empty data.")
    return parent_sha_list


def __get_tag_commit_sha(_tag_exid, repo_full_name=None):  # 示例：https://api.github.com/repos/spree/spree/tags {"name": "v4.7.1", "commit_sha": "bcbf8f28ed189124b1c2e4cf700f170c36e84c85"}
    repo_id = _tag_exid.split('@')[0]
    tag_name = _tag_exid.split('@')[1]
    if not repo_full_name:
        url_params = {
            "repo_id": repo_id
        }
        requestGitHubAPI = RequestGitHubAPI(url_pat_mode='id')
        url = requestGitHubAPI.get_url(url_type="repo", params=url_params)
        response = requestGitHubAPI.request(url)
        if response is not None:
            data = response.json()
            repo_full_name = data["full_name"]
        else:
            print("Error: Cannot find repository.")
            return None

    owner = repo_full_name.split('/')[0]
    repo = repo_full_name.split('/')[1]
    tag_commit_sha = __get_tag_commit_sha_by_GraphQL_API(tag_name, owner, repo)
    if not tag_commit_sha:
        tag_commit_sha = __get_tag_commit_sha_by_REST_API(tag_name, owner, repo)
    return tag_commit_sha


def __get_tag_commit_sha_by_GraphQL_API(tag_name, owner, repo):
    params = {
        "owner": owner,
        "repo": repo,
        "tag_name": tag_name
    }

    # 设置GraphQL查询语句
    QUERY = """
    {
      repository(owner: "OWNER", name: "REPO") {
        ref(qualifiedName: "TAG_NAME") {
          target {
            ... on Commit {
              oid
            }
          }
        }
      }
    }
    """
    QUERY = QUERY.replace("{", "{{").replace("}", "}}")
    QUERY = QUERY.replace("OWNER", "{owner}").replace("REPO", "{repo}").replace("TAG_NAME", "{tag_name}").format(
        **params)
    query_graphql_api = GitHubGraphQLAPI()
    response = query_graphql_api.request(QUERY)
    try:
        data = response.json()
        tag_commit_sha = data['data']['repository']['ref']['target']['oid']
    except BaseException as e:
        tag_commit_sha = None
    return tag_commit_sha


def __get_tag_commit_sha_by_REST_API(tag_name, owner, repo):
    requestGitHubAPI = RequestGitHubAPI()
    url = f'https://api.github.com/repos/{owner}/{repo}/tags'
    response = requestGitHubAPI.request(url)
    tag_commit_sha = None
    if response is not None:
        data = response.json()
        # 解析JSON响应
        df_tags = pd.DataFrame(data)
        df_tag = df_tags[df_tags["name"] == tag_name]
        if len(df_tag):
            d_tag_rec = df_tag.to_dict("records")[0]
            tag_commit = d_tag_rec["commit"]
            tag_commit_sha = tag_commit['sha']
    else:
        print("Empty data.")
    return tag_commit_sha


if __name__ == '__main__':
    print(len(df_Actor), len(df_Repo))

    # test search entities from DataBase
    res = [
        __get_actor_id_by_actor_login("X-lab2017"),
        __get_actor_login_by_actor_id(49427213),
        __get_repo_id_by_repo_full_name("X-lab2017/open-digger"),
        __get_repo_full_name_by_repo_id(288431943),
        _get_field_from_db('push_commits.message', {'type': 'PushEvent', 'repo_id': None, 'push_head': 'eced203d53133650123dc944f758c5f8240b45cb'}),
        _get_field_from_db('actor_id', {'type': 'PushEvent', 'push_head': 'eced203d53133650123dc944f758c5f8240b45cb'}),
        _get_field_from_db('body', {'type': 'CommitCommentEvent', 'commit_comment_id': 93389283}),
        get_actor_id_by_actor_login('birdflyi'),
        get_repo_id_by_repo_full_name('redis/redis')
    ]
    print(res)
    # f = lambda _issue_exid: _get_field_from_db('issue_title', {'type': 'IssuesEvent', 'repo_id': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['repo_id'], 'issue_number': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['issue_number']})
    # print(f("8514#53017"))
    # f = lambda _issue_exid: _get_field_from_db('body', {'type': 'IssuesEvent', 'repo_id': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['repo_id'], 'issue_number': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['issue_number']})
    # print(f("8514#53017"))
    # f = lambda issue_comment_id: _get_field_from_db('body', {'type': 'IssueCommentEvent', 'issue_comment_id': issue_comment_id})
    # print(f(1590332346))
    # f1 = lambda _issue_exid: _get_field_from_db('issue_title', {'type': 'PullRequestEvent', 'repo_id': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['repo_id'], 'issue_number': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['issue_number']})
    # print(f1('8514#52770'))
    # f2 = lambda _issue_exid: _get_field_from_db('body', {'type': 'PullRequestEvent', 'repo_id': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['repo_id'], 'issue_number': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['issue_number']})
    # print(f2('8514#52770'))
    # f = lambda pull_review_id: _get_field_from_db('body', {'type': 'PullRequestReviewEvent', 'pull_review_id': pull_review_id})
    # print(f(1271118857))
    # f = lambda pull_review_comment_id: _get_field_from_db('body', {'type': 'PullRequestReviewCommentEvent', 'pull_review_comment_id': pull_review_comment_id})
    # print(f(1067994666))
    # f = lambda release_id: _get_field_from_db('release_body', {'type': 'ReleaseEvent', 'release_id': release_id})
    # print(f(110927802))
    f = lambda repo_id: _get_field_from_db('repo_description', {'type': 'PullRequestEvent', 'repo_id': repo_id})
    print(f(339104949))

    # # test search entities from GitHUB API
    userinfo = __get_github_userinfo_from_email("cs_zhlou@163.com")
    print(userinfo)

    sha_res = [
        __get_PR_commits_sha_by_issue_exid("288431943#1292"),
        __get_commit_parents_sha("e5b25fba712a6d675fbf8328ef44ae0e1a8e377e", 288431943),
        __get_tag_commit_sha(_tag_exid="3314@v4.7.1", repo_full_name="spree/spree"),
    ]
    print(sha_res)
