#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/10/23 1:41
# @Author : 'Lou Zehua'
# @File   : Entity_search.py

import re
import requests

from script import re_ref_patterns
from script.model.Attribute_getter import get_repo_id_by_repo_full_name, _get_field_from_db, \
    get_actor_id_by_login, __get_github_userinfo_from_email
from script.model.Entity_model import ObjEntity
from utils.conndb import ConnDB
from utils.request_api import GITHUB_TOKEN, GitHubGraphQLAPI

d_link_pattern_type_nt = {
    "Issue_PR": ["Issue", "PullRequest", "IssueComment", "PullRequestReview", "PullRequestReviewComment", "Obj"],
    "SHA": ["Commit", "Obj"],
    "Actor": ["Actor", "Obj"],
    "Repo": ["Repo", "Obj"],
    "Branch_Tag": ["Branch", "Tag", "Obj"],
    "CommitComment": ["CommitComment", "Obj"],
    "Gollum": ["Gollum", "Obj"],
    "Release": ["Release", "Obj"],
    "GitHub_Files": ["Obj"],  # 可以与owner, repo_name关联
    "GitHub_Other_Links": ["Obj"],  # 可以与owner, repo_name关联
    "GitHub_Other_Service": ["Obj"],  # 可以与owner关联，并确定service根网址属性
    "GitHub_Service_External_Links": ["Obj"],
}


def get_nt_list_by_link_pattern_type(link_pattern_type):
    return d_link_pattern_type_nt[link_pattern_type]


# 获取特定issue的详细信息的函数
def get_issue_type(repo_id, issue_number, access_token=GITHUB_TOKEN):
    # 构造请求的URL
    url = f"https://api.github.com/repositories/{repo_id}/issues/{issue_number}"

    # 发送请求
    response = requests.get(url, auth=('token', access_token))

    # 检查请求是否成功
    if response.status_code == 200:
        # 解析响应内容
        issue_data = dict(response.json())

        # 判断issue类型
        if issue_data.get('pull_request', None) is None:
            return 'Issue'
        else:
            return 'PullRequest'
    else:
        print(f"Error fetching issue details: {response.status_code}")
        return None


def get_issue_type_by_repo_id_issue_number(repo_id, issue_number):
    if not repo_id or not issue_number:
        return None

    conndb = ConnDB()
    conndb.sql = f"select type from opensource.events where platform='GitHub' and repo_id={repo_id} and issue_number={issue_number} and action='opened';"
    conndb.execute()

    I_PR_evntType_nodeType_dict = {
        "IssuesEvent": "Issue",
        "PullRequestEvent": "PullRequest",
    }

    if len(conndb.rs):
        event_type = conndb.rs["type"].values[0]
        node_type = I_PR_evntType_nodeType_dict.get(event_type, "Obj")
    else:
        # https://api.github.com/repositories/288431943/issues/1
        node_type = get_issue_type(repo_id, issue_number)
    return node_type


def __get_ref_names_by_repo_name(repo_name, query_node_type='tag'):
    query_node_types = ['branch', 'tag']
    if query_node_type not in query_node_types:
        raise ValueError(f"query_node_type must be in {query_node_types}!")

    # GraphQL查询语句
    query_branches = """
    {
      repository(owner: "%s", name: "%s") {
        refs(refPrefix: "refs/heads/", first: 100) {
          nodes {
            name
          }
        }
      }
    }
    """ % (repo_name.split('/')[0], repo_name.split('/')[1])

    query_tags = """
    {
      repository(owner: "%s", name: "%s") {
        refs(refPrefix: "refs/tags/", first: 100) {
          edges {
            node {
              name
              target {
                ... on Tag {
                  tagger {
                    date
                  }
                  message
                }
              }
            }
          }
        }
      }
    }
    """ % (repo_name.split('/')[0], repo_name.split('/')[1])

    d_query = dict(zip(query_node_types[:2], [query_branches, query_tags]))
    query = d_query[query_node_type]
    query_graphql_api = GitHubGraphQLAPI()
    response = query_graphql_api.request_post(query)
    data = response.json()
    parse_branches = lambda data: [branch['name'] for branch in data['data']['repository']['refs']['nodes']]
    parse_tags = lambda data: [e['node']['name'] for e in data['data']['repository']['refs']['edges']]
    # print(data)
    d_parse_func = dict(zip(query_node_types[:2], [parse_branches, parse_tags]))
    try:
        name_list = d_parse_func[query_node_type](data)
    except BaseException:
        name_list = []
    return name_list


def get_first_match_or_none(pattern, string):
    matches = re.findall(pattern, string)
    return matches[0] if matches else None


# Entity Search
def get_ent_obj_in_link_text(link_pattern_type, link_text, d_record):
    if not link_text:
        return None
    if d_record is None:
        d_record = {}
    link_text = str(link_text)
    nt = None
    d_val = {}
    d_val["match_text"] = link_text
    d_val['match_pattern_type'] = link_pattern_type
    default_node_type = "Obj"
    if link_pattern_type == "Issue_PR":
        if re.search(r"#discussion_r\d+(?![\d#/])", link_text) or re.search(
                r"/files(?:/[0-9a-fA-F]{40})?#r\d+(?![\d#/])", link_text):
            nt = "PullRequestReviewComment"
            # https://github.com/redis/redis/pull/10502/files#r839879682
            # https://github.com/X-lab2017/open-digger/pull/1487/files/17fa11a4cb104bce9feaf9a9bc13003862480219#r1448367800
            # https://github.com/redis/redis/pull/10502#discussion_r839879682
            repo_name = get_first_match_or_none(
                r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?=(?=/issues)|(?=/pull))', link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            issue_number = get_first_match_or_none(r'(?<=(?<=issues/)|(?<=pull/))\d+', link_text)
            pull_review_comment_id = get_first_match_or_none(r'(?<=(?<=#discussion_r)|(?<=#r))\d+', link_text)
            d_val['repo_id'] = repo_id
            d_val['issue_number'] = issue_number
            d_val['pull_review_comment_id'] = pull_review_comment_id
        elif re.search(r"#pullrequestreview-\d+(?![\d#/])", link_text):
            nt = "PullRequestReview"
            # https://github.com/redis/redis/pull/10502#pullrequestreview-927978437
            repo_name = get_first_match_or_none(
                r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?=(?=/issues)|(?=/pull))', link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            issue_number = get_first_match_or_none(r'(?<=(?<=issues/)|(?<=pull/))\d+', link_text)
            pull_review_id = get_first_match_or_none(r'(?<=#pullrequestreview-)\d+', link_text)
            d_val['repo_id'] = repo_id
            d_val['issue_number'] = issue_number
            d_val['pull_review_id'] = pull_review_id
        elif re.search(r"#issuecomment-\d+(?![\d#/])", link_text):
            nt = "IssueComment"
            # 'https://github.com/redis/redis/issues/10472#issuecomment-1126545338',
            repo_name = get_first_match_or_none(
                r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?=(?=/issues)|(?=/pull))', link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            issue_number = get_first_match_or_none(r'(?<=(?<=issues/)|(?<=pull/))\d+', link_text)
            issue_comment_id = get_first_match_or_none(r'(?<=#issuecomment-)\d+', link_text)
            d_val['repo_id'] = repo_id
            d_val['issue_number'] = issue_number
            d_val['issue_comment_id'] = issue_comment_id
        elif re.search(r"/pull/\d+(?![\d#/])", link_text) or re.search(r"/pull/\d+#issue-\d+(?![\d/])", link_text):
            nt = "PullRequest"
            # https://github.com/redis/redis/pull/10587#event-6444202459
            repo_name = get_first_match_or_none(
                r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?=(?=/issues)|(?=/pull))', link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            issue_number = get_first_match_or_none(r'(?<=(?<=issues/)|(?<=pull/))\d+', link_text)
            issue_id = get_first_match_or_none(r'(?<=#issue-)\d+', link_text)
            d_val['repo_id'] = repo_id
            d_val['issue_number'] = issue_number
            d_val['issue_id'] = issue_id
        elif re.search(r"/issues/\d+(?![\d#/])", link_text) or re.search(r"/issues/\d+#issue-\d+(?![\d/])", link_text):
            nt = "Issue"
            # https://github.com/X-lab2017/open-research/issues/123#issue-1406887967
            repo_name = get_first_match_or_none(
                r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?=(?=/issues)|(?=/pull))', link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            issue_number = get_first_match_or_none(r'(?<=(?<=issues/)|(?<=pull/))\d+', link_text)
            issue_id = get_first_match_or_none(r'(?<=#issue-)\d+', link_text)
            d_val['repo_id'] = repo_id
            d_val['issue_number'] = issue_number
            d_val['issue_id'] = issue_id
        else:
            nt = "Obj"
            if re.findall(r"^(?:[Pp][Uu][Ll][Ll]\s?[Rr][Ee][Qq][Uu][Ee][Ss][Tt])(?:#)0*[1-9][0-9]*$", link_text) or \
                    re.findall(r"^(?:[Pp][Rr])(?:#)0*[1-9][0-9]*$", link_text):  # e.g. PR#32
                nt = "PullRequest"
                repo_id = d_record.get("repo_id")  # 传入record的repo_id字段
                issue_number = get_first_match_or_none(r'(?<=#)0*[1-9][0-9]*', link_text)
            elif re.findall(r"^(?:[Ii][Ss][Ss][Uu][Ee][Ss]?)(?:#)0*[1-9][0-9]*$", link_text):  # e.g. issue#32
                nt = "Issue"
                repo_id = d_record.get("repo_id")  # 传入record的repo_id字段
                issue_number = get_first_match_or_none(r'(?<=#)0*[1-9][0-9]*', link_text)
            elif re.findall(r"^(?:#)0*[1-9][0-9]*$", link_text):  # e.g. #782, '#734', '#3221'
                repo_id = d_record.get("repo_id")  # 传入record的repo_id字段
                issue_number = get_first_match_or_none(r'(?<=#)0*[1-9][0-9]*', link_text)
                nt = get_issue_type_by_repo_id_issue_number(repo_id, issue_number) or "Obj"
            elif re.findall(r"^(?:[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*#)\d+$",
                            link_text):  # e.g. redis/redis-doc#1711
                repo_name = get_first_match_or_none(r'[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?=#)',
                                                    link_text)
                repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                    "repo_name") else d_record.get("repo_id")
                issue_number = get_first_match_or_none(r'(?<=#)0*[1-9][0-9]*', link_text)
                nt = get_issue_type_by_repo_id_issue_number(repo_id, issue_number) or "Obj"
            else:
                nt = "Obj"  # obj e.g. 'RB#26080', 'BUG#32134875', 'BUG#31553323'
                repo_id = None
                issue_number = None
            d_val['repo_id'] = repo_id
            d_val['issue_number'] = issue_number
    elif link_pattern_type == "SHA":
        if re.search(r"/commits?/[0-9a-fA-F]{40}$", link_text):
            nt = "Commit"
            # *https://github.com/redis/redis/commit/dcf02298110fabb3c8f0c73c096adfafb64d9134
            # *https://github.com/redis/redis/pull/10502/commits/03b15c81a8300a46990312bdd18bd9f67102d1a0
            repo_name = get_first_match_or_none(
                r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?=(?=/commit)|(?=/pull))', link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            commit_sha = get_first_match_or_none(r'(?<=(?<=commits/)|(?<=commit/))[0-9a-fA-F]{40}', link_text)
            d_val['repo_id'] = repo_id
            d_val['commit_sha'] = commit_sha
        elif re.search(r"^[0-9a-fA-F]{40}$", link_text):
            repo_id = d_record.get("repo_id")
            commit_sha = link_text
            # 使用clickhouse查询；另一种判断方式：使用api判断是否为本仓库的commit https://api.github.com/repos/{repo_name}/git/commits/{sha}
            is_inner_commit_sha = _get_field_from_db('count(*)',
                                                     {'repo_id': repo_id, 'push_head': commit_sha})  # 本仓库的Commit
            if is_inner_commit_sha:
                nt = "Commit"
                d_val['repo_id'] = repo_id
                d_val['commit_sha'] = commit_sha
            else:
                nt = "Obj"
                d_val['repo_id'] = None
                d_val['commit_sha'] = commit_sha
        elif re.search(r"^[0-9a-fA-F]{7}$", link_text):
            repo_id = d_record.get("repo_id")
            sha_abbr_7 = link_text
            conndb = ConnDB()
            sql = f"select push_head from opensource.events where platform='GitHub' and repo_id={repo_id} and push_head like '{sha_abbr_7}%' limit 1"
            df_rs = conndb.query(sql)
            is_inner_commit_sha_abbr_7 = len(df_rs) > 0
            commit_sha = df_rs.iloc[0, 0] if len(df_rs) else None
            if is_inner_commit_sha_abbr_7:
                nt = "Commit"
                d_val['repo_id'] = repo_id
                d_val['commit_sha'] = commit_sha
            else:
                nt = "Obj"
                d_val['repo_id'] = None
                d_val['commit_sha'] = None
        else:
            pass  # should never be reached
    elif link_pattern_type == "Actor":
        if re.findall(r"github(?:-redirect.dependabot)?.com/", link_text):
            nt = "Actor"
            actor_login = get_first_match_or_none(r"(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*(?![-A-Za-z0-9/])", link_text)
            actor_id = get_actor_id_by_login(actor_login) if actor_login != d_record.get(
                "actor_login") else d_record.get("repo_id")
            d_val["actor_login"] = actor_login
            d_val["actor_id"] = actor_id
        elif '@' in link_text:  # @actor_login @normal_text
            nt = "Obj"
            actor_id = None
            if link_text.startswith('@'):
                actor_login = link_text.split('@')[-1]
                actor_id = get_actor_id_by_login(actor_login) if actor_login != d_record.get(
                    "actor_login") else d_record.get("repo_id")
            else:  # e.g. email
                userinfo = __get_github_userinfo_from_email(link_text)
                if userinfo:
                    actor_login = userinfo["login"]
                    actor_id = userinfo["id"]
                else:
                    actor_login = None
                    actor_id = None
            if actor_id:
                nt = "Actor"
                d_val["actor_login"] = actor_login
                d_val["actor_id"] = actor_id
        else:
            pass  # should never be reached
    elif link_pattern_type == "Repo":
        if re.findall(r"github(?:-redirect.dependabot)?.com/", link_text):
            nt = "Repo"
            repo_name = get_first_match_or_none(
                r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?![-_A-Za-z0-9\./])', link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            d_val["repo_name"] = repo_name
            d_val["repo_id"] = repo_id
        else:
            pass  # should never be reached
    elif link_pattern_type == "Branch_Tag":
        if re.findall(r"/tree/[^\s]+", link_text):
            repo_name = get_first_match_or_none(
                r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?![-_A-Za-z0-9\.])', link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            d_val["repo_name"] = repo_name
            d_val["repo_id"] = repo_id

            label_name = get_first_match_or_none(r'(?<=tree/)[^\s#]+$', link_text)
            if label_name:
                if label_name in __get_ref_names_by_repo_name(repo_name, query_node_type="branch"):
                    nt = "Branch"
                    d_val["branch_name"] = label_name
                elif label_name in __get_ref_names_by_repo_name(repo_name, query_node_type="tag"):
                    nt = "Tag"
                    d_val["tag_name"] = label_name
                else:
                    nt = "Obj"
            else:
                if get_first_match_or_none(r'(?<=tree/)[^\s]+$', link_text):
                    return get_ent_obj_in_link_text("GitHub_Files", link_text, d_record)
                else:
                    nt = "Obj"
        else:
            pass  # should never be reached
    elif link_pattern_type == "CommitComment":
        if re.findall(r"commit/[0-9a-fA-F]{40}#commitcomment-\d+(?![\d#/])", link_text):
            nt = "CommitComment"
            repo_name = get_first_match_or_none(r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*',
                                                link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            commit_comment_id = get_first_match_or_none(r'(?<=#commitcomment-)\d+', link_text)
            d_val["repo_name"] = repo_name
            d_val["repo_id"] = repo_id
            d_val["commit_comment_id"] = commit_comment_id
        else:
            pass  # should never be reached
    elif link_pattern_type == "Gollum":
        if re.findall(r"/wiki/[-_A-Za-z0-9\.%#/:]*(?![-_A-Za-z0-9\.%#/:])", link_text):
            nt = "Gollum"
            repo_name = get_first_match_or_none(
                r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?=/wiki)', link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            d_val["repo_name"] = repo_name
            d_val["repo_id"] = repo_id
        else:
            pass  # should never be reached
    elif link_pattern_type == "Release":
        if re.findall(r"/releases/tag/[^\s]+", link_text):
            nt = "Release"
            repo_name = get_first_match_or_none(r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*',
                                                link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            release_id = d_record.get("release_id")
            release_name = get_first_match_or_none(r'(?<=/releases/tag/)[^\s]+', link_text)
            d_val["repo_name"] = repo_name
            d_val["repo_id"] = repo_id
            d_val["release_id"] = release_id
            d_val["release_name"] = release_name
        else:
            pass  # should never be reached
    elif link_pattern_type == "GitHub_Files":
        nt = "Obj"
        repo_name = get_first_match_or_none(r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*', link_text)
        repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get("repo_name") else d_record.get(
            "repo_id")
        d_val["repo_name"] = repo_name
        d_val["repo_id"] = repo_id
    elif link_pattern_type == "GitHub_Other_Links":
        nt = "Obj"
        repo_name = get_first_match_or_none(r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*', link_text)
        repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get("repo_name") else d_record.get(
            "repo_id")
        d_val["repo_name"] = repo_name
        d_val["repo_id"] = repo_id
    elif link_pattern_type == "GitHub_Other_Service":
        nt = "Obj"
        actor_login = get_first_match_or_none(r"(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*(?![-A-Za-z0-9/])", link_text)
        actor_id = get_actor_id_by_login(actor_login) if actor_login != d_record.get("actor_login") else d_record.get(
            "repo_id")
        d_val["actor_login"] = actor_login if actor_id else None
        d_val["actor_id"] = actor_id
    elif link_pattern_type == "GitHub_Service_External_Links":
        nt = "Obj"
    else:
        pass  # should never be reached
    ent_obj = ObjEntity(nt)
    ent_obj.set_val(d_val)
    return ent_obj


if __name__ == '__main__':
    print(get_issue_type_by_repo_id_issue_number(288431943, 1552))
    print(__get_ref_names_by_repo_name('birdflyi/test', query_node_type="branch"))

    temp_link_text = """
    redis/redis#123
    https://github.com/redis/redis/issues/10587#issue-6444202459
    https://github.com/X-lab2017/open-digger/issues/1585#issue-2387584247
    """
    d_link_text = {
        "Issue_PR_0 strs_all subs": ['https://github.com/X-lab2017/open-research/issues/123#issue-1406887967',
                                     'https://github.com/X-lab2017/open-digger/pull/1038#issue-1443186854',
                                     'https://github.com/X-lab2017/open-galaxy/pull/2#issuecomment-982562221',
                                     'https://github.com/X-lab2017/open-galaxy/pull/2#pullrequestreview-818986332',
                                     'https://github.com/openframeworks/openFrameworks/pull/7383#discussion_r1411384813'],
        "Issue_PR_1 strs_all subs": ['https://github-redirect.dependabot.com/python-babel/babel/issues/782',
                                     'https://github-redirect.dependabot.com/python-babel/babel/issues/734',
                                     'http://www.github.com/xxx/xx/issues/3221'],
        "Issue_PR_2 strs_all subs": ['https://github.com/xxx/xx/pull/3221'],
        "Issue_PR_3 strs_all subs": [
            'https://github.com/openframeworks/openFrameworks/pull/7383/files/1f9efefc25685f062c03ebfbd2832c6e47481d01#r1411384813',
            'https://github.com/openframeworks/openFrameworks/pull/7383/files#r1411384813'],
        "Issue_PR_4 strs_all subs": ['#782', 'RB#26080', 'BUG#32134875', 'BUG#31553323', '#734', '#3221', 'issue#32'],
        "SHA_0 strs_all subs": [
            'https://github.com/X-lab2017/open-galaxy/pull/2/commits/7f9f3706abc7b5a9ad37470519f5066119ba46c2'],
        "SHA_1 strs_all subs": ['https://www.github.com/xxx/xx/commit/5c9a6c06871cb9fe42814af9c039eb6da5427a6e'],
        "SHA_2 strs_all subs": ['5c9a6c06871cb9fe42814af9c039eb6da5427a6e'],
        "SHA_3 strs_all subs": ['5c9a6c1', '5c9a6c2', '5c9a6c0'],
        "Actor_0 strs_all subs": ['https://github.com/birdflyi'],
        "Actor_1 strs_all subs": ['@danxmoran1', '@danxmoran2', '@danxmoran3', '@birdflyi', '@author', '@danxmoran4',
                                  '@danxmoran5'],
        "Actor_2 strs_all subs": ['author@abc.com'],
        "Repo_0 strs_all subs": ['https://github.com/X-lab2017/open-research'],
        "Branch_Tag_0 strs_all subs": ['https://github.com/birdflyi/test/tree/\'"-./()<>!%40',
                                       'https://github.com/openframeworks/openFrameworks/tree/master',
                                       'https://github.com/birdflyi/test/tree/v\'"-./()<>!%40%2540'],
        "CommitComment_0 strs_all subs": [
            'https://github.com/JuliaLang/julia/commit/5a904ac97a89506456f5e890b8dabea57bd7a0fa#commitcomment-144873925'],
        "Gollum_0 strs_all subs": ['https://github.com/activescaffold/active_scaffold/wiki/API:-FieldSearch'],
        "Release_0 strs_all subs": ['https://github.com/rails/rails/releases/tag/v7.1.2',
                                    'https://github.com/birdflyi/test/releases/tag/v\'"-.%2F()<>!%40%2540'],
        "GitHub_Files_0 strs_all subs": [
            'https://github.com/roleoroleo/yi-hack-Allwinner/files/5136276/y25ga_0.1.9.tar.gz'],
        "GitHub_Files_1 strs_all subs": [
            'https://github.com/X-lab2017/open-digger/pull/997/files#diff-5cda5bb2aa8682c3b9d4dbf864efdd6100fe1a5f748941d972204412520724e5'],
        "GitHub_Files_2 strs_all subs": [
            'https://github.com/birdflyi/Research-Methods-of-Cross-Science/blob/main/%E4%BB%8E%E7%A7%91%E5%AD%A6%E8%B5%B7%E6%BA%90%E7%9C%8B%E4%BA%A4%E5%8F%89%E5%AD%A6%E7%A7%91.md'],
        "GitHub_Other_Links_0 strs_all subs": ['https://github.com/X-lab2017/open-digger/labels/pull%2Fhypertrons'],
        "GitHub_Other_Service_0 strs_all subs": ['https://gist.github.com/birdflyi'],
        "GitHub_Service_External_Links_0 strs_all subs": ['http://sqlite.org/forum/forumpost/fdb0bb7ad0',
                                                          'https://sqlite.org/forum/forumpost/fdb0bb7ad0']
    }

    link_text = '\n'.join([e_i for e in d_link_text.values() for e_i in e]) + temp_link_text
    print(re.findall(re_ref_patterns["Issue_PR"][0], link_text))
    results = []
    for link_pattern_type in re_ref_patterns.keys():
        for link in re.findall(re_ref_patterns["Issue_PR"][0], link_text):
            obj = get_ent_obj_in_link_text(link_pattern_type, link, d_record=None)
            results.append(obj)
        break
    print(results[0].__dict__)
