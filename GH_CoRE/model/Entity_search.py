#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/10/23 1:41
# @Author : 'Lou Zehua'
# @File   : Entity_search.py

import re
from urllib.parse import quote, unquote

import pandas as pd

from GH_CoRE.data_dict_settings import re_ref_patterns
from GH_CoRE.model.Attribute_getter import get_repo_id_by_repo_full_name, _get_field_from_db, \
    get_actor_id_by_actor_login, __get_github_userinfo_from_email, get_repo_name_by_repo_id, __get_issue_type
from GH_CoRE.model.Entity_model import ObjEntity
from GH_CoRE.utils.request_api import GitHubGraphQLAPI, RequestGitHubAPI

d_link_pattern_type_nt = {
    "Issue_PR": ["Issue", "PullRequest", "IssueComment", "PullRequestReview", "PullRequestReviewComment", "Obj"],
    "SHA": ["Commit", "Obj"],
    "Actor": ["Actor", "Obj"],
    "Repo": ["Repo", "Obj"],
    "Branch_Tag_GHDir": ["Branch", "Tag", "Obj"],
    "CommitComment": ["CommitComment", "Obj"],
    "Gollum": ["Gollum", "Obj"],
    "Release": ["Release", "Obj"],
    "GitHub_Files_FileChanges": ["Obj"],  # 可以与owner, repo_name关联
    "GitHub_Other_Links": ["Obj"],  # 可以与owner, repo_name关联
    "GitHub_Other_Service": ["Obj"],  # 可以与owner关联，并确定service根网址属性
    "GitHub_Service_External_Links": ["Obj"],
}

URL_ESCAPE_CHARS = "_-.'/()!"


def escape_double_quote_marks(s, auto=True):
    if auto and "\"" not in s:
        s_esc_quote = s
    else:
        try:
            s_esc_quote = s.replace("\\", r"\\").replace("\"", r"\"")
        except BaseException:
            s_esc_quote = s
    return s_esc_quote


def get_nt_list_by_link_pattern_type(link_pattern_type):
    return d_link_pattern_type_nt[link_pattern_type]


def encode_urls(path_list, safe=URL_ESCAPE_CHARS):
    return [quote(path, safe=safe) for path in path_list]


def get_issue_type_by_repo_id_issue_number(repo_id, issue_number):
    if not repo_id or not issue_number:
        return None

    event_type = _get_field_from_db('type', {"repo_id": repo_id, "issue_number": issue_number, "action": "opened"})

    I_PR_evntType_nodeType_dict = {
        "IssuesEvent": "Issue",
        "PullRequestEvent": "PullRequest",
    }
    if event_type:
        node_type = I_PR_evntType_nodeType_dict.get(event_type, "Obj")
    else:
        node_type = __get_issue_type(repo_id, issue_number)
    return node_type


def __get_ref_name_exists_flag_by_repo_name(ref_name, repo_name, query_node_type='tag'):
    ref_name = escape_double_quote_marks(ref_name)
    query_node_types = ['branch', 'tag']
    if query_node_type not in query_node_types:
        raise ValueError(f"query_node_type must be in {query_node_types}!")
    # GraphQL查询语句
    query_branch_by_name = """
    query {
      repository(owner: "%s", name: "%s") {
        ref(qualifiedName: "refs/heads/%s") { 
          target {
            ... on Node {
              id
            }
          }
        }
      }
    }
    """ % (repo_name.split('/')[0], repo_name.split('/')[1], ref_name)

    query_tag_by_name = """
    query {
      repository(owner: "%s", name: "%s") {
        ref(qualifiedName: "refs/tags/%s") {
          target {
            ... on Node {
              id
            }
          }
        }
      }
    }
    """ % (repo_name.split('/')[0], repo_name.split('/')[1], ref_name)  # (r"v'\"-./()<>!@%40", "birdflyi/test", query_node_type='tag')

    d_query = {"query_node_types": query_node_types[:2],
               "query_statements": [query_branch_by_name, query_tag_by_name],
               "variables": [{}, {}]}
    df_query = pd.DataFrame(d_query)
    query = df_query[df_query["query_node_types"] == query_node_type]["query_statements"].values[0]
    variables = df_query[df_query["query_node_types"] == query_node_type]["variables"].values[0]
    query_graphql_api = GitHubGraphQLAPI()
    response = query_graphql_api.request(query, params=variables)
    data = response.json()
    get_ref_dict = lambda data: data["data"]["repository"]["ref"]
    try:
        ref_dict = get_ref_dict(data)
        ref_id = ref_dict["target"]["id"]
    except BaseException:
        ref_id = None
    ref_name_exists_flag = ref_id is not None
    return ref_name_exists_flag


def __get_ref_names_by_repo_name(repo_name, query_node_type='tag'):
    query_node_types = ['branch', 'tag']
    if query_node_type not in query_node_types:
        raise ValueError(f"query_node_type must be in {query_node_types}!")

    # GraphQL查询语句
    query_branches = """
    query ($after: String) {
      repository(owner: "%s", name: "%s") {
        refs(refPrefix: "refs/heads/", first: 100, after: $after) {
          edges {
            node {
              name
            }
            cursor
          }
          pageInfo {
            endCursor
            hasNextPage
          }
        }
      }
    }
    """ % (repo_name.split('/')[0], repo_name.split('/')[1])
    variables_branches = {"after": None}

    query_tags = """
    query ($after: String) {
      repository(owner: "%s", name: "%s") {
        refs(refPrefix: "refs/tags/", first: 100, after: $after) {
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
            cursor
          }
          pageInfo {
            endCursor
            hasNextPage
          }
        }
      }
    }
    """ % (repo_name.split('/')[0], repo_name.split('/')[1])
    variables_tags = {"after": None}

    d_query = {"query_node_types": query_node_types[:2],
               "query_statements": [query_branches, query_tags],
               "variables": [variables_branches, variables_tags]}
    df_query = pd.DataFrame(d_query)
    query = df_query[df_query["query_node_types"] == query_node_type]["query_statements"].values[0]
    variables = df_query[df_query["query_node_types"] == query_node_type]["variables"].values[0]
    variables = {} if variables is None else dict(variables)
    query_graphql_api = GitHubGraphQLAPI()
    response = query_graphql_api.request(query, variables=variables)
    data = response.json()
    get_ref_names = lambda data: [edge["node"]["name"] for edge in data["data"]["repository"]["refs"]["edges"]]
    get_page_info = lambda data: data["data"]["repository"]["refs"]["pageInfo"]
    try:
        name_list = get_ref_names(data)
        page_info = get_page_info(data)
        while page_info["hasNextPage"]:
            variables.update(**{"after": page_info["endCursor"]})
            response_cur_page = query_graphql_api.request(query, variables=variables)
            data_cur_page = response_cur_page.json()
            name_list_cur_page = get_ref_names(data_cur_page)
            name_list.extend(name_list_cur_page)
            page_info = get_page_info(data_cur_page)
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
    objnt_prop_dict = None
    d_val = {"match_text": link_text, "match_pattern_type": link_pattern_type, "objnt_prop_dict": objnt_prop_dict}
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
            d_val['repo_name'] = repo_name
            d_val['issue_number'] = issue_number
            d_val['pull_review_comment_id'] = pull_review_comment_id
            objnt_prop_dict = {"issue_number": issue_number, 'pull_review_comment_id': pull_review_comment_id}
            d_val['objnt_prop_dict'] = objnt_prop_dict
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
            d_val['repo_name'] = repo_name
            d_val['issue_number'] = issue_number
            d_val['pull_review_id'] = pull_review_id
            objnt_prop_dict = {"issue_number": issue_number, 'pull_review_id': pull_review_id}
            d_val['objnt_prop_dict'] = objnt_prop_dict
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
            d_val['repo_name'] = repo_name
            d_val['issue_number'] = issue_number
            d_val['issue_comment_id'] = issue_comment_id
            objnt_prop_dict = {"issue_number": issue_number, 'issue_comment_id': issue_comment_id}
            d_val['objnt_prop_dict'] = objnt_prop_dict
        elif re.search(r"/pull/\d+(?![\d#/])", link_text) or re.search(r"/pull/\d+#[-_0-9a-zA-Z\.%#/:]+-\d+(?![\d/])", link_text):
            nt = "PullRequest"
            # https://github.com/redis/redis/pull/10587#event-6444202459
            repo_name = get_first_match_or_none(
                r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?=(?=/issues)|(?=/pull))', link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            issue_number = get_first_match_or_none(r'(?<=(?<=issues/)|(?<=pull/))\d+', link_text)
            issue_elemName_elemIds = get_first_match_or_none(r'(?<=#)[-_0-9a-zA-Z\.%#/:]+-\d+', link_text)
            objnt_prop_dict = {"issue_number": issue_number}
            if issue_elemName_elemIds:
                try:
                    issue_elemName_elemId = issue_elemName_elemIds[0]
                    issue_elemName = '-'.join(issue_elemName_elemId.split('-')[:-1])
                    issue_elemId = issue_elemName_elemId.split('-')[-1]
                    objnt_prop_dict[issue_elemName] = issue_elemId
                except BaseException:
                    pass
            d_val['repo_id'] = repo_id
            d_val['repo_name'] = repo_name
            d_val['issue_number'] = issue_number
            d_val['objnt_prop_dict'] = objnt_prop_dict
        elif re.search(r"/issues/\d+(?![\d#/])", link_text) or re.search(r"/issues/\d+#[-_0-9a-zA-Z\.%#/:]+-\d+(?![\d/])", link_text):
            nt = "Issue"
            # https://github.com/X-lab2017/open-research/issues/123#issue-1406887967
            repo_name = get_first_match_or_none(
                r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?=(?=/issues)|(?=/pull))', link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            issue_number = get_first_match_or_none(r'(?<=(?<=issues/)|(?<=pull/))\d+', link_text)
            issue_elemName_elemIds = get_first_match_or_none(r'(?<=#)[-_0-9a-zA-Z\.%#/:]+-\d+', link_text)
            objnt_prop_dict = {"issue_number": issue_number}
            if issue_elemName_elemIds:
                try:
                    issue_elemName_elemId = issue_elemName_elemIds[0]
                    issue_elemName = '-'.join(issue_elemName_elemId.split('-')[:-1])
                    issue_elemId = issue_elemName_elemId.split('-')[-1]
                    objnt_prop_dict[issue_elemName] = issue_elemId
                except BaseException:
                    pass
            d_val['repo_id'] = repo_id
            d_val['repo_name'] = repo_name
            d_val['issue_number'] = issue_number
            d_val['objnt_prop_dict'] = objnt_prop_dict
        elif re.search(r".*#0*[1-9][0-9]*(?![\d/#a-z])", link_text):
            repo_id = None
            repo_name = None
            if re.findall(r"(?i)^(?:Pull\s?Request)(?:#)0*[1-9][0-9]*$", link_text) or \
                    re.findall(r"(?i)^(?:PR)(?:#)0*[1-9][0-9]*$", link_text):  # e.g. PR#32
                nt = "PullRequest"
                if d_record.get("repo_id"):
                    repo_id = repo_id or d_record.get("repo_id")  # 传入record的repo_id字段
                    repo_name = repo_name or d_record.get("repo_name") or get_repo_name_by_repo_id(repo_id)
                elif d_record.get("repo_name"):
                    repo_name = repo_name or d_record.get("repo_name")
                    repo_id = repo_id or d_record.get("repo_id") or get_repo_id_by_repo_full_name(repo_name)
                issue_number = get_first_match_or_none(r'(?<=#)0*[1-9][0-9]*', link_text)
            elif re.findall(r"(?i)^(?:Issues?)(?:#)0*[1-9][0-9]*$", link_text):  # e.g. issue#32
                nt = "Issue"
                if d_record.get("repo_id"):
                    repo_id = repo_id or d_record.get("repo_id")  # 传入record的repo_id字段
                    repo_name = repo_name or d_record.get("repo_name") or get_repo_name_by_repo_id(repo_id)
                elif d_record.get("repo_name"):
                    repo_name = repo_name or d_record.get("repo_name")
                    repo_id = repo_id or d_record.get("repo_id") or get_repo_id_by_repo_full_name(repo_name)
                issue_number = get_first_match_or_none(r'(?<=#)0*[1-9][0-9]*', link_text)
            elif re.findall(r"^(?:#)0*[1-9][0-9]*$", link_text):  # e.g. #782, '#734', '#3221'
                issue_number = get_first_match_or_none(r'(?<=#)0*[1-9][0-9]*', link_text)
                if d_record.get("repo_id"):
                    repo_id = d_record.get("repo_id")  # 传入record的repo_id字段
                    repo_name = d_record.get("repo_name") or get_repo_name_by_repo_id(repo_id)
                elif d_record.get("repo_name"):
                    repo_name = d_record.get("repo_name")
                    repo_id = d_record.get("repo_id") or get_repo_id_by_repo_full_name(repo_name)
                nt = get_issue_type_by_repo_id_issue_number(repo_id, issue_number) or "Obj"  # uncertain
            elif re.findall(r"^(?:[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*#)\d+$", link_text):  # e.g. redis/redis-doc#1711
                repo_name = get_first_match_or_none(r'[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?=#)',
                                                    link_text)
                repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                    "repo_name") else d_record.get("repo_id")
                issue_number = get_first_match_or_none(r'(?<=#)0*[1-9][0-9]*', link_text)
                nt = get_issue_type_by_repo_id_issue_number(repo_id, issue_number) or "Obj"  # uncertain
            else:
                nt = "Obj"  # obj e.g. 'RB#26080', 'BUG#32134875', 'BUG#31553323'
                issue_number = None

            if nt == "Obj":
                objnt_prop_dict = {"numbers": re.findall(r"(?<=#)\d+", link_text)}
                if link_text.startswith('http'):  # 以http开头必可被其他pattern识别，此处被重复识别
                    objnt_prop_dict["label"] = "Text_Locator"
                    objnt_prop_dict["duplicate_matching"] = True
            elif issue_number is not None:
                objnt_prop_dict = {"issue_number": issue_number}
            else:
                objnt_prop_dict = {"numbers": re.findall(r"(?<=#)\d+", link_text)}

            d_val['repo_id'] = repo_id
            d_val['repo_name'] = repo_name
            d_val['issue_number'] = issue_number
            d_val["objnt_prop_dict"] = objnt_prop_dict
        else:  # should never be reached
            pass
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
            d_val['repo_name'] = repo_name
            d_val['commit_sha'] = commit_sha
            objnt_prop_dict = {"commit_sha": commit_sha}
            d_val['objnt_prop_dict'] = objnt_prop_dict
        elif re.search(r"^[0-9a-fA-F]{40}$", link_text):
            repo_id = d_record.get("repo_id")
            repo_name = d_record.get("repo_name")
            if repo_id:
                repo_name = repo_name or get_repo_name_by_repo_id(repo_id)
            elif repo_name:
                repo_id = repo_id or get_repo_id_by_repo_full_name(repo_name)

            commit_sha = link_text
            # 使用clickhouse查询；另一种判断方式：使用api判断是否为本仓库的commit https://api.github.com/repos/{repo_name}/git/commits/{sha}
            is_inner_commit_sha = _get_field_from_db('TRUE',
                                                     {'repo_id': repo_id, 'push_head': commit_sha})  # 本仓库的Commit
            is_outer_commit_sha = False
            # if not is_inner_commit_sha:
            #     # 可在clickhouse中查询到的Commit，会超出clickhouse的最大内存限制
            #     repo_id_ck = _get_field_from_db('repo_id', {'push_head': commit_sha})
            #     if repo_id_ck:
            #         repo_id = repo_id_ck
            #         repo_name = get_repo_name_by_repo_id(repo_id)
            #         is_outer_commit_sha = True
            find_sha_by_ck = is_inner_commit_sha or is_outer_commit_sha
            if not find_sha_by_ck:  # is_inner_commit_sha and is_outer_commit_sha == False
                requestGitHubAPI = RequestGitHubAPI(url_pat_mode='id')
                get_commit_url = requestGitHubAPI.get_url("commit", params={"repo_id": repo_id, "commit_sha": commit_sha})
                response = requestGitHubAPI.request(get_commit_url)
                if response:
                    commit_sha = response.json().get('sha', None)
                    is_inner_commit_sha = True  # repo_id, repo_name保持不变
                else:
                    response = None  # 由于Clickhouse在仅知道sha情况下查询日志会超出内存限制，而GitHub API查询完整sha需要repo_id，因此repo_id未知时不再作直接根据sha查询记录的尝试
                    is_outer_commit_sha = bool(response)
            find_sha_by_api = is_inner_commit_sha or is_outer_commit_sha
            if find_sha_by_ck or find_sha_by_api:
                nt = "Commit"
                objnt_prop_dict = {"commit_sha": commit_sha}
            else:  # 可能是查询的异常
                nt = "Obj"  # uncertain
                repo_id = None
                repo_name = None
                objnt_prop_dict = {"sha": link_text, "status": "QuickSearchFailed", "label": "SHA"}
                d_val["objnt_prop_dict"] = objnt_prop_dict
                commit_sha = None
            d_val['repo_id'] = repo_id
            d_val['repo_name'] = repo_name
            d_val['commit_sha'] = commit_sha
            d_val['objnt_prop_dict'] = objnt_prop_dict
        elif re.search(r"[0-9a-fA-F]{7}$", link_text):
            repo_id = d_record.get("repo_id")
            repo_name = d_record.get("repo_name")
            if repo_id:
                repo_name = repo_name or get_repo_name_by_repo_id(repo_id)
            elif repo_name:
                repo_id = repo_id or get_repo_id_by_repo_full_name(repo_name)
            sha_abbr_7 = get_first_match_or_none(r'[0-9a-fA-F]{7}$', link_text)
            if 'COMMIT' in link_text.upper() or 'SHA' in link_text.upper():
                nt = 'Commit'
            elif sha_abbr_7 is None or str.isdigit(link_text):  # 未包含COMMIT与SHA的前缀且link_text全是数字，仍然是sha的事件是极小概率事件
                nt = 'Obj'
            else:  # still unknown
                nt = None

            if nt == 'Obj':
                repo_id = None
                repo_name = None
                commit_sha = None
                objnt_prop_dict = {"label": "NotAnEntity"}
            else:  # 'Commit' or None
                commit_sha = _get_field_from_db('push_head', {'repo_id': repo_id, 'push_head': f"like '{sha_abbr_7}%'"})  # 本仓库的Commit
                is_inner_commit_sha = bool(commit_sha)
                is_outer_commit_sha = False
                # if not is_inner_commit_sha:
                #     # 可在clickhouse中查询到的Commit，会超出clickhouse的最大内存限制
                #     df_rs = _get_field_from_db('repo_id, push_head', {'push_head': f"like '{sha_abbr_7}%'"}, dataframe_format=True)
                #     repo_id_ck = df_rs.iloc[0, 0] if len(df_rs) else None
                #     commit_sha = df_rs.iloc[0, 1] if len(df_rs) else None
                #     if repo_id_ck:
                #         repo_id = repo_id_ck
                #         repo_name = get_repo_name_by_repo_id(repo_id)
                #         is_outer_commit_sha = True
                find_sha_by_ck = is_inner_commit_sha or is_outer_commit_sha
                if not find_sha_by_ck:  # is_inner_commit_sha and is_outer_commit_sha == False
                    requestGitHubAPI = RequestGitHubAPI(url_pat_mode='id')
                    get_commit_url = requestGitHubAPI.get_url("commit", params={"repo_id": repo_id, "commit_sha": sha_abbr_7})
                    response = requestGitHubAPI.request(get_commit_url)
                    if response:
                        commit_sha = response.json().get('sha', None)
                        is_inner_commit_sha = True
                    else:  # response为空，sha与d_record的repo_id不匹配
                        response = None  # 由于Clickhouse在仅知道sha情况下查询日志会超出内存限制，而GitHub API查询完整sha需要repo_id，因此repo_id未知时不再作直接根据sha查询记录的尝试
                        is_outer_commit_sha = bool(response)
                find_sha_by_api = is_inner_commit_sha or is_outer_commit_sha
                if find_sha_by_ck or find_sha_by_api:
                    nt = "Commit"
                    objnt_prop_dict = {"sha_abbr_7": link_text, "commit_sha": commit_sha}
                else:
                    repo_id = None
                    repo_name = None
                    commit_sha = None
                    if nt == "Commit":  # 也可能是查询的异常
                        if 'COMMIT' in link_text.upper():
                            nt = "Commit"
                            objnt_prop_dict = {"sha_abbr_7": link_text, "status": "QuickSearchFailed", "label": "Commit SHA"}
                        else:
                            nt = "Obj"
                            objnt_prop_dict = {"sha_abbr_7": link_text, "status": "QuickSearchFailed", "label": "SHA"}
                    else:
                        nt = "Obj"  #  uncertain，nt为None时重置为默认值Obj
                        objnt_prop_dict = {"sha_abbr_7": link_text}

            d_val['repo_id'] = repo_id
            d_val['repo_name'] = repo_name
            d_val['commit_sha'] = commit_sha
            d_val["objnt_prop_dict"] = objnt_prop_dict
        else:
            pass  # should never be reached
    elif link_pattern_type == "Actor":
        if re.findall(r"github(?:-redirect.dependabot)?.com/", link_text):
            nt = "Actor"
            actor_login = get_first_match_or_none(r"(?<=com/)([A-Za-z0-9][-0-9a-zA-Z]*(?:\[bot\])?)(?![-A-Za-z0-9/])", link_text)
            actor_id = get_actor_id_by_actor_login(actor_login) if actor_login != d_record.get(
                "actor_login") else d_record.get("actor_id")
            objnt_prop_dict = {"actor_id": actor_id, "actor_login": actor_login}
            d_val["actor_login"] = actor_login
            d_val["actor_id"] = actor_id
            d_val["objnt_prop_dict"] = objnt_prop_dict
        elif '@' in link_text:  # @actor_login @normal_text
            if link_text.startswith('@'):
                actor_login = link_text.split('@', 1)[-1]
                actor_id = get_actor_id_by_actor_login(actor_login) if actor_login != d_record.get(
                    "actor_login") else d_record.get("actor_id")
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
                objnt_prop_dict = {"actor_id": actor_id, "actor_login": actor_login}
            else:
                nt = "Obj"
                actor_login = None
                actor_id = None
                objnt_prop_dict = {"at_str": link_text.split('@')[-1]}
            d_val["actor_login"] = actor_login
            d_val["actor_id"] = actor_id
            d_val["objnt_prop_dict"] = objnt_prop_dict
        else:
            pass  # should never be reached
    elif link_pattern_type == "Repo":
        if re.findall(r"github(?:-redirect.dependabot)?.com/", link_text):
            nt = "Repo"
            repo_name_pattern_substr = get_first_match_or_none(
                r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?![-_A-Za-z0-9\./])', link_text)
            if str(repo_name_pattern_substr).startswith("orgs/"):
                actor_login = repo_name_pattern_substr.split('orgs/', 1)[-1]
                nt = default_node_type
                if actor_login:
                    if actor_login == d_record.get("org_login"):
                        actor_id = d_record.get("org_id")
                    elif actor_login == d_record.get("actor_login"):
                        actor_id = d_record.get("actor_id")
                    else:
                        actor_id = get_actor_id_by_actor_login(actor_login)
                    if actor_id:
                        nt = "Actor"
                        objnt_prop_dict = objnt_prop_dict or {}
                        objnt_prop_dict["label"] = "Organization"
                        objnt_prop_dict["org_login"] = actor_login
                        objnt_prop_dict["org_id"] = actor_id
                        d_val["actor_login"] = actor_login
                        d_val["actor_id"] = actor_id
                        d_val["objnt_prop_dict"] = objnt_prop_dict
            else:
                repo_name = repo_name_pattern_substr
                if repo_name.endswith(".git"):
                    repo_name = repo_name[:-4]
                elif repo_name.endswith("."):
                    repo_name = repo_name[:-1]
                repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                    "repo_name") else d_record.get("repo_id")
                if repo_id:
                    objnt_prop_dict = {"repo_id": repo_id, "repo_name": repo_name}
                else:
                    nt = "Obj"  # uncertain
                    objnt_prop_dict = None
                d_val["repo_name"] = repo_name
                d_val["repo_id"] = repo_id
                d_val["objnt_prop_dict"] = objnt_prop_dict
        else:
            pass  # should never be reached
    elif link_pattern_type == "Branch_Tag_GHDir":
        if re.findall(r"/tree/[^\s]+", link_text):
            repo_name = get_first_match_or_none(
                r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?![-_A-Za-z0-9\.])', link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")

            Branch_Tag_GHDir_name = get_first_match_or_none(r'(?<=tree/)[^\s#]+$', link_text)
            if Branch_Tag_GHDir_name:
                Branch_Tag_GHDir_name = str(Branch_Tag_GHDir_name)
                Branch_Tag_GHDir_name_url_dec = unquote(Branch_Tag_GHDir_name)
                branch_ref_name_exists = __get_ref_name_exists_flag_by_repo_name(Branch_Tag_GHDir_name, repo_name, query_node_type="branch")
                branch_ref_name_dec_exists = __get_ref_name_exists_flag_by_repo_name(Branch_Tag_GHDir_name_url_dec, repo_name, query_node_type="branch")
                if branch_ref_name_exists or branch_ref_name_dec_exists:
                    nt = "Branch"
                    d_val["branch_name"] = Branch_Tag_GHDir_name
                    objnt_prop_dict = {"branch_name": Branch_Tag_GHDir_name}
                else:
                    tag_ref_name_exists = __get_ref_name_exists_flag_by_repo_name(Branch_Tag_GHDir_name, repo_name, query_node_type="tag")
                    tag_ref_name_dec_exists = __get_ref_name_exists_flag_by_repo_name(Branch_Tag_GHDir_name_url_dec, repo_name, query_node_type="tag")
                    if tag_ref_name_exists or tag_ref_name_dec_exists:
                        if Branch_Tag_GHDir_name_url_dec != Branch_Tag_GHDir_name and tag_ref_name_dec_exists:
                            Branch_Tag_GHDir_name = Branch_Tag_GHDir_name_url_dec
                        nt = "Tag"
                        d_val["tag_name"] = Branch_Tag_GHDir_name
                        objnt_prop_dict = {"tag_name": Branch_Tag_GHDir_name}
                    else:
                        nt = "Obj"  # GitHub_Dir
                        label = None
                        objnt_prop_dict = {}
                        if "#" in Branch_Tag_GHDir_name:
                            label = "Text_Locator"
                        elif "/" in Branch_Tag_GHDir_name:
                            label = "GitHub_Dir"
                        if label is not None:
                            objnt_prop_dict["label"] = label
            else:
                nt = "Obj"  # repo_id repo_name仍保留
                objnt_prop_dict = None

            d_val["repo_name"] = repo_name
            d_val["repo_id"] = repo_id
            d_val["objnt_prop_dict"] = objnt_prop_dict
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
            objnt_prop_dict = {"commit_comment_id": commit_comment_id}
            d_val["repo_name"] = repo_name
            d_val["repo_id"] = repo_id
            d_val["commit_comment_id"] = commit_comment_id
            d_val["objnt_prop_dict"] = objnt_prop_dict
        else:
            pass  # should never be reached
    elif link_pattern_type == "Gollum":
        if re.findall(r"/wiki/[-_A-Za-z0-9\.%#/:]*(?![-_A-Za-z0-9\.%#/:])", link_text):
            nt = "Gollum"
            repo_name = get_first_match_or_none(
                r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*(?=/wiki)', link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            objnt_prop_dict = None
            d_val["repo_name"] = repo_name
            d_val["repo_id"] = repo_id
            d_val["objnt_prop_dict"] = objnt_prop_dict
        else:
            pass  # should never be reached
    elif link_pattern_type == "Release":
        if re.findall(r"/releases/tag/[^\s]+", link_text):
            nt = "Release"
            tag_query_status = None
            repo_name = get_first_match_or_none(r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*',
                                                link_text)
            repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get(
                "repo_name") else d_record.get("repo_id")
            release_tag_name = get_first_match_or_none(r'(?<=/releases/tag/)[^\s]+', link_text)
            release_tag_name_url_dec = unquote(release_tag_name)
               
            if release_tag_name == d_record.get("release_tag_name") or release_tag_name_url_dec == d_record.get("release_tag_name"):
                if release_tag_name_url_dec == d_record.get("release_tag_name"):
                    release_tag_name = release_tag_name_url_dec
                release_id = d_record.get("release_id")
            else:
                release_id = _get_field_from_db('release_id', {"repo_id": repo_id, "release_tag_name": release_tag_name})
                if release_tag_name != release_tag_name_url_dec and not release_id:
                    release_id = _get_field_from_db('release_id',
                                                    {"repo_id": repo_id, "release_tag_name": release_tag_name_url_dec})
                    if release_id:
                        release_tag_name = release_tag_name_url_dec
                if not release_id:  # This may be a tag, but not a release tag.
                    nt = "Tag"
                    tag_name = release_tag_name
                    tag_query_status = "failure"
                    tag_ref_name_exists = __get_ref_name_exists_flag_by_repo_name(release_tag_name, repo_name, query_node_type="tag")
                    tag_ref_name_dec_exists = __get_ref_name_exists_flag_by_repo_name(release_tag_name_url_dec, repo_name, query_node_type="tag")
                    if tag_ref_name_exists or tag_ref_name_dec_exists:
                        tag_query_status = "success"
                        if release_tag_name_url_dec != release_tag_name and tag_ref_name_dec_exists:
                            tag_name = release_tag_name_url_dec
                    release_id = None
                    release_tag_name = None
                    d_val["tag_name"] = tag_name
                    objnt_prop_dict = {"tag_name": tag_name, "tag_query_status": tag_query_status}
            if tag_query_status is None:
                objnt_prop_dict = {"release_id": release_id, "release_tag_name": release_tag_name}
            d_val["repo_name"] = repo_name
            d_val["repo_id"] = repo_id
            d_val["release_id"] = release_id
            d_val["release_tag_name"] = release_tag_name
            d_val["objnt_prop_dict"] = objnt_prop_dict
        else:
            pass  # should never be reached
    elif link_pattern_type == "GitHub_Files_FileChanges":
        nt = "Obj"
        repo_name = get_first_match_or_none(r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*', link_text)
        repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get("repo_name") else d_record.get(
            "repo_id")
        d_val["repo_name"] = repo_name
        d_val["repo_id"] = repo_id
    elif link_pattern_type == "GitHub_Other_Links":
        nt = "Obj"
        org_repo_name = get_first_match_or_none(r'(?<=com/)[A-Za-z0-9][-0-9a-zA-Z]*/[A-Za-z0-9][-_0-9a-zA-Z\.]*', link_text)
        org_repo_name = str(org_repo_name)
        if org_repo_name:
            objnt_prop_dict = {}
            if org_repo_name.startswith('orgs/'):
                actor_login = org_repo_name.split('orgs/', 1)[-1]
                repo_name = None
            else:
                actor_login = None
                repo_name = org_repo_name
            if actor_login:
                if actor_login == d_record.get("org_login"):
                    actor_id = d_record.get("org_id")
                elif actor_login == d_record.get("actor_login"):
                    actor_id = d_record.get("actor_id")
                else:
                    actor_id = get_actor_id_by_actor_login(actor_login)
                if actor_id:
                    nt = "Actor"
                    objnt_prop_dict = objnt_prop_dict or {}
                    objnt_prop_dict["label"] = "Organization"
                    objnt_prop_dict["org_login"] = actor_login
                    objnt_prop_dict["org_id"] = actor_id
                    d_val["actor_login"] = actor_login
                    d_val["actor_id"] = actor_id
                    d_val["objnt_prop_dict"] = objnt_prop_dict
            if repo_name:
                repo_id = get_repo_id_by_repo_full_name(repo_name) if repo_name != d_record.get("repo_name") else d_record.get(
                    "repo_id")
                d_val["repo_name"] = repo_name
                d_val["repo_id"] = repo_id
                objnt_prop_dict["repo_name"] = repo_name
                objnt_prop_dict["repo_id"] = repo_id

            d_val["objnt_prop_dict"] = objnt_prop_dict
    elif link_pattern_type == "GitHub_Other_Service":
        nt = "Obj"
        actor_login = get_first_match_or_none(r"(?<=com/apps/)([A-Za-z0-9][-0-9a-zA-Z]*(?:\[bot\])?)(?![-A-Za-z0-9/])", link_text)
        actor_id = get_actor_id_by_actor_login(actor_login) if actor_login != d_record.get(
            "actor_login") else d_record.get("actor_id")
        if actor_id:
            nt = 'Actor'
            objnt_prop_dict = {"actor_id": actor_id, "actor_login": actor_login, "label": "Bot"}
            d_val["actor_login"] = actor_login
            d_val["actor_id"] = actor_id
            d_val["objnt_prop_dict"] = objnt_prop_dict
    elif link_pattern_type == "GitHub_Service_External_Links":
        nt = "Obj"
    else:
        pass  # should never be reached

    if d_val.get("repo_id"):
        objnt_prop_dict = {"repo_name": d_val.get("repo_name"), "repo_id": d_val.get("repo_id")}
        d_extra_prop = d_val.get("objnt_prop_dict", None)
        if d_extra_prop:
            objnt_prop_dict.update(d_extra_prop)
    d_val["objnt_prop_dict"] = objnt_prop_dict
    if not isinstance(nt, str):
        print(f"The node type is {nt}! It will be parsed into {default_node_type} by default! You may need to check "
              f"if you have overlooked handling certain boundary situations!"
              f"\r\n\tCurrent d_val = {d_val}.")
        nt = default_node_type
    ent_obj = ObjEntity(nt)
    ent_obj.set_val(d_val)
    return ent_obj


if __name__ == '__main__':
    print(get_issue_type_by_repo_id_issue_number(288431943, 1552))
    print(__get_ref_names_by_repo_name('birdflyi/test', query_node_type="branch"))
    branch_name = "'\"-./()<>!@"
    print(branch_name, __get_ref_name_exists_flag_by_repo_name(branch_name, 'birdflyi/test', query_node_type="branch"))
    tag_name = "v'\"-./()<>!@%40"
    print(tag_name, __get_ref_name_exists_flag_by_repo_name(tag_name, 'birdflyi/test', query_node_type="tag"))

    temp_link_text = """
    redis/redis#123
    https://github.com/redis/redis/issues/10587#issue-6444202459
    https://github.com/X-lab2017/open-digger/issues/1585#issue-2387584247
    https://github.com/facebook/rocksdb/blob/main/HISTORY.md#800
    https://github.com/facebook/rocksdb/releases/tag/v8.3.2
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
        "Issue_PR_4 strs_all subs": ['https://github.com/facebook/rocksdb/blob/main/HISTORY.md#840', '#782', 'RB#26080',
                                     'BUG#32134875', 'BUG#31553323', '#734', '#3221', 'issue#32'],
        "SHA_0 strs_all subs": [
            'https://github.com/X-lab2017/open-galaxy/pull/2/commits/7f9f3706abc7b5a9ad37470519f5066119ba46c2'],
        "SHA_1 strs_all subs": ['https://www.github.com/xxx/xx/commit/5c9a6c06871cb9fe42814af9c039eb6da5427a6e'],
        "SHA_2 strs_all subs": ['5c9a6c06871cb9fe42814af9c039eb6da5427a6e'],
        "SHA_3 strs_all subs": ['5c9a6c1', '5c9a6c2', '5c9a6c0'],
        "Actor_0 strs_all subs": ['https://github.com/birdflyi'],
        "Actor_1 strs_all subs": ['@danxmoran1', '@danxmoran2', '@danxmoran3', '@birdflyi', '@author', '@danxmoran4',
                                  '@danxmoran5'],
        "Actor_2 strs_all subs": ['author@abc.com'],
        "Repo_0 strs_all subs": ['https://github.com/TW-Genesis/rocksdb-bench.git', 'https://github.com/afs/TDB3.git',
                                 'https://github.com/tikv/rocksdb.', 'https://github.com/intel/ipp-crypto.',
                                 'https://github.com/X-lab2017/open-research'],
        "Branch_Tag_GHDir_0 strs_all subs": [
            'https://github.com/elastic/elasticsearch/tree/main/docs#test-code-snippets',
            'https://github.com/artificialinc/elasticsearch/tree/aidan/8-10-0-default-azure-credential',
            'https://github.com/birdflyi/test/tree/\'"-./()<>!%40',
            'https://github.com/openframeworks/openFrameworks/tree/master',
            'https://github.com/birdflyi/test/tree/v\'"-./()<>!%40%2540'],
        "CommitComment_0 strs_all subs": [
            'https://github.com/JuliaLang/julia/commit/5a904ac97a89506456f5e890b8dabea57bd7a0fa#commitcomment-144873925'],
        "Gollum_0 strs_all subs": ['https://github.com/activescaffold/active_scaffold/wiki/API:-FieldSearch'],
        "Release_0 strs_all subs": ['https://github.com/rails/rails/releases/tag/v7.1.2',
                                    'https://github.com/birdflyi/test/releases/tag/v\'"-.%2F()<>!%40%2540'],
        "GitHub_Files_FileChanges_0 strs_all subs": [
            'https://github.com/roleoroleo/yi-hack-Allwinner/files/5136276/y25ga_0.1.9.tar.gz'],
        "GitHub_Files_FileChanges_1 strs_all subs": [
            'https://github.com/X-lab2017/open-digger/pull/997/files#diff-5cda5bb2aa8682c3b9d4dbf864efdd6100fe1a5f748941d972204412520724e5'],
        "GitHub_Files_FileChanges_2 strs_all subs": [
            'https://github.com/facebook/rocksdb/blob/main/HISTORY.md#840-06262023',
            'https://github.com/birdflyi/Research-Methods-of-Cross-Science/blob/main/%E4%BB%8E%E7%A7%91%E5%AD%A6%E8%B5%B7%E6%BA%90%E7%9C%8B%E4%BA%A4%E5%8F%89%E5%AD%A6%E7%A7%91.md'],
        "GitHub_Other_Links_0 strs_all subs": ['https://github.com/X-lab2017/open-digger/labels/pull%2Fhypertrons'],
        "GitHub_Other_Service_0 strs_all subs": ['https://gist.github.com/birdflyi'],
        "GitHub_Other_Service_1 strs_all subs": ['https://github.com/apps/dependabot'],
        "GitHub_Service_External_Links_0 strs_all subs": ['http://sqlite.org/forum/forumpost/fdb0bb7ad0',
                                                          'https://sqlite.org/forum/forumpost/fdb0bb7ad0']
    }

    # link_text = '\n'.join([e_i for e in d_link_text.values() for e_i in e]) + temp_link_text
    # print(re.findall(re_ref_patterns["Issue_PR"][0], link_text))
    link_text = """
    http://127.0.0.1:7001]
    @dnz
    https://github.com/orgs/cockroachdb
    https://github.com/orgs/cockroachdb/teams/storage
    https://github.com/birdflyi/test/tree/'\"-./()<>!%40
    https://github.com/cockroachdb/cockroach/releases/tag/%40cockroachlabs%2Fcluster-ui%4024.3.2
    https://github.com/apps/exalate-issue-sync[bot]
    @exalate-issue-sync[bot]
    cockroachlabs/blathers-bot#92
    Friendly ping on this one as well @andrewbaptis.
    Friendly ping on this one as well @andrewbaptis.(edited)
    """

    from GH_CoRE.working_flow import mask_code

    results = []
    for link_pattern_type in re_ref_patterns.keys():
        for i in range(len(re_ref_patterns[link_pattern_type])):
            for link in re.findall(re_ref_patterns[link_pattern_type][i], mask_code(link_text)):
                obj = get_ent_obj_in_link_text(link_pattern_type, link, d_record={'repo_name': 'cockroachdb/cockroach', 'repo_id': 16563587})
                results.append(obj)

    for i, res in enumerate(results):
        print(i, results[i].__type__, results[i].get_dict())

    obj = get_ent_obj_in_link_text("SHA", "50982bb7b64d620c9e5270930cc2963a2f97100e",
                                   d_record={'repo_name': 'TuGraph-family/tugraph-db'})
    print(obj.__type__, obj.get_dict())
