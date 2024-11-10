#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/10/22 22:45
# @Author : 'Lou Zehua'
# @File   : Entity_model.py

import inspect
import re
import types

import numpy as np

# __get_tag_commit_sha must be imported, see ER_config.event_trigger_ERE_triples_dict
from GH_CoRE.model.Attribute_getter import _get_field_from_db, get_actor_id_by_actor_login, \
    get_repo_id_by_repo_full_name, __get_commit_parents_sha, __get_tag_commit_sha
from GH_CoRE.model.ER_config_parser import get_eventType_params_from_joined_str


class Obj_exid:
    exid_map = {
        "branch_exid": "{repo_id}:{branch_name}",
        "gollum_exid": "{repo_id}:wiki",
        "issue_exid": "{repo_id}#{issue_number}",
        "tag_exid": "{repo_id}@{tag_name}"
    }
    exid_seps = [':', '#', '@']

    @staticmethod
    def _match_exid_map_key(exid_map_key, match_conditon='endswith'):
        if match_conditon == "equal":
            match_func = lambda s_in, s: str(s_in) == str(s)
        elif match_conditon == "endswith":
            match_func = lambda s_in, s: str(s_in).endswith(str(s))
        else:
            raise ValueError("match_conditon must be in ['equal', 'endswith']!")
        key_list = list(Obj_exid.exid_map.keys())
        k_matched_list = [s for s in key_list if match_func(exid_map_key, s)]
        k_matched = None
        if len(k_matched_list):
            k_matched = k_matched_list[0]
            if len(k_matched_list) > 1:
                print(f"Warning: Find multiple keys: {k_matched_list}, use {k_matched_list[0]}.")
        else:
            raise ValueError("Cannot find any matched key in exid_map!")
        return k_matched

    @staticmethod
    def get_exid(exid_map_key, d_params, match_conditon='endswith'):
        k_matched = Obj_exid._match_exid_map_key(exid_map_key, match_conditon)
        d_params_validate = True
        for v in d_params.values():
            d_params_validate = d_params_validate and v
        if not (k_matched and d_params_validate):  # 有空值
            return None
        d_params = {str(k): str(v) for k, v in d_params.items()}
        exid_string = Obj_exid.exid_map[k_matched].format(**d_params)
        return exid_string

    @staticmethod
    def get_kwargs_from_exid(exid_map_key, exid_string, match_conditon='endswith'):
        k_matched = Obj_exid._match_exid_map_key(exid_map_key, match_conditon)
        exid_template = Obj_exid.exid_map[k_matched]

        temp_sep = None
        for sep in Obj_exid.exid_seps:
            if sep not in exid_string:
                temp_sep = sep
                break
        if not temp_sep:
            temp_sep = Obj_exid.exid_seps[0]
            print(
                f"Warning: The exid_string contains all separators! Use {Obj_exid.exid_seps[0]} as the default separator!")

        exid_template_prepared = exid_template
        exid_string_prepared = exid_string
        for sep in Obj_exid.exid_seps:
            exid_template_prepared = exid_template_prepared.replace(sep, temp_sep)
            exid_string_prepared = exid_string_prepared.replace(sep, temp_sep)

        keys = [k.strip("{}") for k in exid_template_prepared.split(temp_sep) if k.strip("{}")]
        values = exid_string_prepared.split(temp_sep)

        exid_kwargs = None
        if len(keys) <= len(values):
            if len(keys) < len(values):
                def find_first_occurrence(char, text):
                    try:
                        return text.index(char)
                    except ValueError:
                        return -1  # 如果字符不在字符串中，返回-1

                d_sep_first_indexes = {}
                ambiguous_pattern = False
                for sep in Obj_exid.exid_seps:
                    sep_first_index = find_first_occurrence(sep, exid_template)
                    if d_sep_first_indexes.get(sep, None) is not None:
                        ambiguous_pattern = True
                    d_sep_first_indexes[sep] = sep_first_index
                if ambiguous_pattern:
                    print(f"Find ambiguous sep pattern in {exid_template} using the same separator multi-times, which "
                          f"may cause wrong parse result when execute get_kwargs_from_exid! "
                          f"Please change the exid_template in Obj_exid.exid_map and Obj_exid.exid_seps.")
                d_sep_first_indexes_sorted_by_val = sorted(d_sep_first_indexes.items(), key=lambda x: x[1])
                d_sep_first_indexes_sorted_by_val = dict(d_sep_first_indexes_sorted_by_val)
                values = []
                curr_raw_str = exid_string
                for sep, ind in d_sep_first_indexes_sorted_by_val.items():
                    if ind >= 0:
                        v_str, curr_raw_str = curr_raw_str.split(sep, 1)
                        values.append(v_str)
                values.append(curr_raw_str)
                if len(values) < len(keys):
                    values += [''] * (len(keys) - len(values))
                values = values[:len(keys)]
                print(
                    f"Warning: the values length is less than the keys length! It will be separated at "
                    f"the position of the first sep in the order it appears in the pattern {exid_template}, "
                    f"and the result may be incorrect: \n\t{keys}, {values}")
            else:
                pass
            exid_kwargs = dict(zip(keys, values))
        else:
            print(
                f"Cannot match exid_template and exid_string: \n\texid_template: {exid_template}, exid_string: {exid_string}.")
        return exid_kwargs


def _trim_refs_heads(ref_str: str):  # see ER_config.event_trigger_ERE_triples_dict
    ref_prefix = "refs/heads/"
    if ref_str.startswith(ref_prefix):
        ref_str_trimmed = ref_str[len(ref_prefix):]
    else:
        ref_str_trimmed = ref_str
    return ref_str_trimmed


# 实体型Entity Type：E(U, D, F)，其中E为实体名，U为组成该实体概念的属性名集合，D为属性组U中属性所来自的域，F为属性间数据的依赖关系集合。
class ObjEntity(object):
    nt_label_delimiter = "::"
    E = {
        'Actor': {
            'U_K': {'actor_id(PK)', 'actor_login'},  # Not None: any
            'U_V': None,
            'D': {'actor_id(PK)': int, 'actor_login': str},
            'F': {'actor_id': lambda actor_login: get_actor_id_by_actor_login(actor_login),  # execute when actor_id is missing
                  'actor_login': lambda actor_id: _get_field_from_db('actor_login', {'actor_id': actor_id}),
                  },
        },
        'Branch': {
            'U_K': {'_branch_exid(PK)', 'repo_id', 'branch_name'},
            # Not None: ['_branch_exid'] or ['repo_id', 'branch_name'], branch_name需要按事件解析并作为实参输入
            'U_V': None,
            'D': {'_branch_exid(PK)': str, 'repo_id': int, 'branch_name': str},
            'F': {'_branch_exid': lambda repo_id, branch_name: Obj_exid.get_exid('_branch_exid', {"repo_id": repo_id,
                                                                                                  "branch_name": branch_name}),
                  'repo_id': lambda _branch_exid: Obj_exid.get_kwargs_from_exid('_branch_exid', _branch_exid)[
                      'repo_id'],
                  'branch_name': lambda _branch_exid: Obj_exid.get_kwargs_from_exid('_branch_exid', _branch_exid)[
                      'branch_name'],
                  },
        },
        'Commit': {
            'U_K': {'commit_sha(PK)', 'repo_id', '_commit_author_id', '__commit_parents_sha'},
            # Not None: ['commit_sha']
            'U_V': {'push_commits.message', 'push_commits.name', 'push_commits.email'},
            'D': {'commit_sha(PK)': str, 'repo_id': int, '_commit_author_id': int, '__commit_parents_sha': list,
                  'push_commits.message': str, 'push_commits.name': str, 'push_commits.email': str},
            # __commit_parents_sha示例：getJson(https://api.github.com/repos/tidyverse/ggplot2/commits/8041c84bf958285fa16301204ac464422373e589).parents.[i].sha
            'F': {'_commit_author_id': lambda commit_sha, type=None, actor_id=None: actor_id if type == 'PushEvent' and ObjEntity.val_not_na(actor_id) else _get_field_from_db('actor_id', {'type': 'PushEvent', 'push_head': commit_sha}),
                  'repo_id': lambda commit_sha: _get_field_from_db('repo_id', {'type': 'PushEvent', 'push_head': commit_sha}),
                  '__commit_parents_sha': lambda commit_sha, repo_id: __get_commit_parents_sha(commit_sha, repo_id),
                  'push_commits.message': lambda commit_sha: _get_field_from_db('push_commits.message', {'type': 'PushEvent', 'push_head': commit_sha}),
                  'push_commits.name': lambda commit_sha: _get_field_from_db('push_commits.name', {'type': 'PushEvent', 'push_head': commit_sha}),
                  'push_commits.email': lambda commit_sha: _get_field_from_db('push_commits.email', {'type': 'PushEvent', 'push_head': commit_sha}),
                  },
        },
        'CommitComment': {
            'U_K': {'commit_comment_id(PK)', 'commit_comment_author_id', 'commit_comment_sha'},
            # Not None: ['commit_comment_id']
            'U_V': {'body', 'commit_comment_path'},  # regard 'commit_comment_path' as unknown NE
            'D': {'commit_comment_id(PK)': int, 'commit_comment_author_id': int, 'commit_comment_sha': str,
                  'body': str, 'commit_comment_path': str},
            'F': {'body': lambda commit_comment_id: _get_field_from_db('body', {'type': 'CommitCommentEvent',
                                                                                'commit_comment_id': commit_comment_id}),
                  'commit_comment_path': lambda commit_comment_id: _get_field_from_db('commit_comment_path', {'type': 'CommitCommentEvent',
                                                                                'commit_comment_id': commit_comment_id})
                  },
        },
        'Gollum': {
            'U_K': {'_gollum_exid(PK)', 'repo_id'},  # Not None: ['repo_id']
            'U_V': None,
            'D': {'_gollum_exid(PK)': str, 'repo_id': int},
            'F': {'_gollum_exid': lambda repo_id: Obj_exid.get_exid('_gollum_exid', {"repo_id": repo_id}),
                  'repo_id': lambda _gollum_exid: Obj_exid.get_kwargs_from_exid('_gollum_exid', _gollum_exid)[
                      'repo_id'],
                  },
        },
        'Issue': {
            'U_K': {'_issue_exid(PK)', 'issue_id', 'repo_id', 'issue_number', 'issue_author_id'},
            # Not None: ['repo_id', 'issue_number']
            'U_V': {'issue_title', 'body'},
            'D': {'_issue_exid(PK)': str, 'issue_id': int, 'repo_id': int, 'issue_number': int, 'issue_author_id': int,
                  'issue_title': str, 'body': str},
            'F': {'_issue_exid': lambda repo_id, issue_number: Obj_exid.get_exid('_issue_exid', {"repo_id": repo_id,
                                                                                                 "issue_number": issue_number}),
                  'repo_id': lambda _issue_exid: Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['repo_id'],
                  'issue_number': lambda _issue_exid: Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)[
                      'issue_number'],
                  'issue_title': lambda repo_id, issue_number: _get_field_from_db('issue_title', {'type': 'IssuesEvent',
                                                                                                  'repo_id': repo_id,
                                                                                                  'issue_number': issue_number}),
                  'body': lambda repo_id, issue_number: _get_field_from_db('body',
                                                                           {'type': 'IssuesEvent', 'repo_id': repo_id,
                                                                            'issue_number': issue_number})
                  },
        },
        'IssueComment': {
            'U_K': {'issue_comment_id(PK)', '_issue_exid', 'repo_id', 'issue_number', 'issue_comment_author_id'},
            # Not None: ['issue_comment_id']
            'U_V': {'body'},
            'D': {'issue_comment_id(PK)': int, '_issue_exid': str, 'repo_id': int, 'issue_number': int,
                  'issue_comment_author_id': int, 'body': str},
            'F': {'_issue_exid': lambda repo_id, issue_number: Obj_exid.get_exid('_issue_exid', {"repo_id": repo_id,
                                                                                                 "issue_number": issue_number}),
                  'body': lambda issue_comment_id: _get_field_from_db('body', {'type': 'IssueCommentEvent',
                                                                               'issue_comment_id': issue_comment_id})
                  },
        },
        'PullRequest': {
            'U_K': {'_issue_exid(PK)', 'issue_id', 'repo_id', 'issue_number', 'issue_author_id',
                    'pull_merge_commit_sha', 'pull_merged_by_id', '_pull_base_branch_exid',
                    'pull_base_ref', '_pull_head_branch_exid', 'pull_head_repo_id', 'pull_head_ref'},
            # Not None: ['repo_id', 'issue_number']
            'U_V': {'issue_title', 'body'},
            'D': {'_issue_exid(PK)': str, 'issue_id': int, 'repo_id': int, 'issue_number': int, 'issue_author_id': int,
                  'pull_merge_commit_sha': str,
                  'pull_merged_by_id': int, '_pull_base_branch_exid': str, 'pull_base_ref': str,
                  '_pull_head_branch_exid': str, 'pull_head_repo_id': int,
                  'pull_head_ref': str, 'issue_title': str, 'body': str},
            'F': {'_issue_exid': lambda repo_id, issue_number: Obj_exid.get_exid('_issue_exid', {"repo_id": repo_id,
                                                                                                 "issue_number": issue_number}),
                  '_pull_base_branch_exid': lambda repo_id, pull_base_ref: Obj_exid.get_exid('_pull_base_branch_exid',
                                                                                             {"repo_id": repo_id,
                                                                                              "branch_name": pull_base_ref}),
                  '_pull_head_branch_exid': lambda pull_head_repo_id, pull_head_ref: Obj_exid.get_exid(
                      '_pull_head_branch_exid', {"repo_id": pull_head_repo_id, "branch_name": pull_head_ref}),
                  'repo_id': lambda _issue_exid: Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['repo_id'],
                  'issue_number': lambda _issue_exid: Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)[
                      'issue_number'],
                  'issue_title': lambda repo_id, issue_number: _get_field_from_db('issue_title',
                                                                                  {'type': 'PullRequestEvent',
                                                                                   'repo_id': repo_id,
                                                                                   'issue_number': issue_number}),
                  'body': lambda repo_id, issue_number: _get_field_from_db('body',
                                                                           {'type': 'PullRequestEvent',
                                                                            'repo_id': repo_id,
                                                                            'issue_number': issue_number})
                  },
        },
        'PullRequestReview': {
            'U_K': {'pull_review_id(PK)', '_issue_exid', 'repo_id', 'issue_id', 'issue_number',
                    'pull_requested_reviewer_id', '_pull_head_branch_exid', 'pull_head_repo_id',
                    'pull_head_ref'},  # Not None: ['pull_review_id']
            'U_V': {'body'},
            'D': {'pull_review_id(PK)': int, '_issue_exid': str, 'repo_id': int, 'issue_id': int, 'issue_number': int,
                  'pull_requested_reviewer_id': int,
                  '_pull_head_branch_exid': str, 'pull_head_repo_id': int, 'pull_head_ref': str, 'body': str},
            'F': {'_issue_exid': lambda repo_id, issue_number: Obj_exid.get_exid('_issue_exid', {"repo_id": repo_id,
                                                                                                 "issue_number": issue_number}),
                  '_pull_head_branch_exid': lambda pull_head_repo_id, pull_head_ref: Obj_exid.get_exid(
                      '_pull_head_branch_exid', {"repo_id": pull_head_repo_id, "branch_name": pull_head_ref}),
                  'body': lambda pull_review_id: _get_field_from_db('body', {'type': 'PullRequestReviewEvent',
                                                                             'pull_review_id': pull_review_id})
                  }
        },
        'PullRequestReviewComment': {
            'U_K': {'pull_review_comment_id(PK)', '_issue_exid', 'repo_id', 'issue_id', 'issue_number',
                    'pull_review_id', 'pull_review_comment_author_id',
                    'push_head'},  # Not None: ['pull_review_comment_id']
            'U_V': {'body', 'pull_review_comment_path'},  # regard 'pull_review_comment_path' as unknown NE
            'D': {'pull_review_comment_id(PK)': int, '_issue_exid': str, 'repo_id': int, 'issue_id': int,
                  'issue_number': int, 'pull_review_id': int,
                  'pull_review_comment_author_id': int, 'push_head': str, 'body': str, 'pull_review_comment_path': str},
            'F': {'_issue_exid': lambda repo_id, issue_number: Obj_exid.get_exid('_issue_exid', {"repo_id": repo_id,
                                                                                                 "issue_number": issue_number}),
                  'body': lambda pull_review_comment_id: _get_field_from_db('body',
                                                                            {'type': 'PullRequestReviewCommentEvent',
                                                                             'pull_review_comment_id': pull_review_comment_id}),
                  'pull_review_comment_path': lambda pull_review_comment_id: _get_field_from_db('pull_review_comment_path',
                                                                            {'type': 'PullRequestReviewCommentEvent',
                                                                             'pull_review_comment_id': pull_review_comment_id})
                  },
        },
        'Push': {
            'U_K': {'push_id(PK)', 'actor_id', '_push_branch_exid', 'repo_id', 'push_ref', 'push_head'},
            # Not None: ['push_id']
            'U_V': None,
            'D': {'push_id(PK)': int, 'actor_id': int, '_push_branch_exid': str, 'repo_id': int, 'push_ref': str,
                  'push_head': str},
            'F': {'_push_branch_exid': lambda repo_id, push_ref: Obj_exid.get_exid('_push_branch_exid',
                                                                                   {"repo_id": repo_id,
                                                                                    "branch_name": _trim_refs_heads(
                                                                                        push_ref)})}
        },
        'Release': {
            'U_K': {'release_id(PK)', 'release_author_id', '_release_tag_exid', 'repo_id', 'release_tag_name',
                    'release_name'},  # Not None: ['release_id']
            'U_V': {'release_body'},
            'D': {'release_id(PK)': int, 'release_author_id': int, '_release_tag_exid': str, 'repo_id': int,
                  'release_tag_name': str, 'release_name': str, 'release_body': str},
            'F': {'_release_tag_exid': lambda repo_id, release_tag_name: Obj_exid.get_exid('_release_tag_exid',
                                                                                           {"repo_id": repo_id,
                                                                                            "tag_name": release_tag_name}),
                  'release_body': lambda release_id: _get_field_from_db('release_body', {'type': 'ReleaseEvent',
                                                                                         'release_id': release_id})
                  },
        },
        'Repo': {
            'U_K': {'repo_id(PK)', '_repo_full_name', 'repo_name', '_owner_id', '_name', 'org_id'},
            # Not None: ['rep_id']
            'U_V': {'repo_description'},
            'D': {'rep_id(PK)': int, '_repo_full_name': str, 'repo_name': str, '_owner_id': int, '_name': str,
                  'org_id': int, 'repo_description': str},
            'F': {'repo_id': lambda repo_name: get_repo_id_by_repo_full_name(repo_name),  # execute when repo_id is missing
                  'repo_name': lambda repo_id: _get_field_from_db('repo_name', {'repo_id': repo_id}),
                  '_repo_full_name': lambda repo_name: repo_name,
                  '_owner_id': lambda repo_name, actor_id=None, actor_login=None: actor_id if actor_login == repo_name.split('/')[0] and ObjEntity.val_not_na(actor_id) else get_actor_id_by_actor_login(repo_name.split('/')[0]),
                  '_name': lambda repo_name: repo_name.split('/')[1],
                  'repo_description': lambda repo_id: _get_field_from_db('repo_description', {'type': 'PullRequestEvent', 'repo_id': repo_id}),
            },
        },
        'Tag': {
            'U_K': {'_tag_exid(PK)', 'repo_id', 'tag_name', '_tag_branch_exid', 'tag_branch_name'},
            # Not None: ['rep_id', 'tag_name'], tag_name, tag_branch_name需解析并输入
            'U_V': None,
            'D': {'_tag_exid(PK)': str, 'repo_id': int, 'tag_name': str, '_tag_branch_exid': str,
                  'tag_branch_name': str},
            'F': {'_tag_exid': lambda repo_id, tag_name: Obj_exid.get_exid('_tag_exid',
                                                                           {"repo_id": repo_id, "tag_name": tag_name}),
                  'repo_id': lambda _tag_exid: Obj_exid.get_kwargs_from_exid('_tag_exid', _tag_exid)['repo_id'],
                  'tag_name': lambda _tag_exid: Obj_exid.get_kwargs_from_exid('_tag_exid', _tag_exid)['tag_name'],
                  # 'tag_name': case(type, [CreateEvent, DeleteEvent, ReleaseEvent], [create_ref, delete_ref, release_tag_name]),
                  '_tag_branch_exid': lambda repo_id, tag_branch_name: Obj_exid.get_exid('_tag_branch_exid',
                                                                                         {"repo_id": repo_id,
                                                                                          "branch_name": tag_branch_name}),
                  # 'tag_branch_name': case(type, [CreateEvent, DeleteEvent, ReleaseEvent], [create_master_branch, None, release_target_commitish]),
                  # '_tag_commit_sha': lambda repo_id, tag_name: __get_tag_commit_sha(repo_id, tag_name)  # 此关系被定义为Tag向Commit的依赖关系，这里不再重复查询
                  },
        },
    }

    def __init__(self, entity_type: str, init_mode='build_id', U_init_scope: list = None):
        self.__type__raw = entity_type
        self.__type__ = entity_type.split(ObjEntity.nt_label_delimiter)[0] if isinstance(entity_type, str) else None
        if init_mode not in ['build_id', 'query_other_fileds_in_F_by_id', 'build_all_fields']:
            raise ValueError("init_mode must be in ['build_id', 'query_other_fileds_in_F_by_id', 'build_all_fields']!")
        self._init_mode = init_mode
        self.__entity_def = dict(ObjEntity.E.get(self.__type__, {}))
        self._U_init_scope = U_init_scope or ['U_K']  # set ['U_K', 'U_V'] to query clickhouse to get all body values.
        temp_field_set_list = [self.__entity_def.get(k, set()) for k in self._U_init_scope]
        self._U_fields = set.union(*temp_field_set_list)
        self.__PK__ = None
        self._neo4j_feat = {}
        for p in self._U_fields:
            if not isinstance(p, str):
                raise TypeError(f"'{p}' in 'U_K' or 'U_V' must be a str type.")
            p = str(p)
            if p.endswith('(PK)'):
                p = p.rstrip('(PK)')
                self.__PK__ = p
            setattr(self, p, None)
            getattr(self, p)
        temp_U_fields = {p.rstrip('(PK)') if p.endswith('(PK)') else p for p in self._U_fields}
        self._U_fields = temp_U_fields
        self.fieldnames = []

    @staticmethod
    def val_is_na(v):
        if isinstance(v, float):
            is_na = np.isnan(v)
        else:
            is_na = v is None
        return is_na

    @staticmethod
    def val_not_na(v):
        return not ObjEntity.val_is_na(v)

    def set_val(self, d_val: dict, extend_field=True):
        var_names = self.get_var_names()
        fieldnames = list(set(list(d_val.keys()) + list(var_names))) if extend_field else var_names
        self.fieldnames = fieldnames
        for p in fieldnames:
            if d_val.get(p, None):
                setattr(self, p, d_val.get(p))  # self->p := d_val[p]

        if self.__type__raw.__contains__(ObjEntity.nt_label_delimiter):  # e.g. 'Commit::commit_sha=commit_comment_sha'
            node_type, d_params = tuple(get_eventType_params_from_joined_str(self.__type__raw, delimiter=ObjEntity.nt_label_delimiter, default_val=None))
            setattr(self, "__type__", node_type)
            for k, v in d_params.items():
                if d_val.get(v):
                    setattr(self, k, d_val.get(v))
                else:
                    v_str = str(v)  # e.g. __get_tag_commit_sha(_tag_exid, _repo_full_name)
                    if v_str.startswith("_") and v_str.endswith(")"):
                        v_vars_strs = re.findall(r"\([_a-zA-Z0-9, ]+\)", v_str)
                        if v_vars_strs:
                            v_str = re.sub(r"\s", "", v_str)
                            v_self = re.sub(r"\(", "(self.", v_str)
                            v_self = re.sub(r",", ",self.", v_self)  # __get_tag_commit_sha(self._tag_exid,self._repo_full_name)
                            try:
                                setattr(self, k, eval(v_self))
                            except BaseException:
                                pass
        self.apply_F()
        try:
            self._neo4j_feat["_id"] = f"{self.__type__}_{getattr(self, self.__PK__)}"
            self._neo4j_feat["_labels"] = ":" + str(self.__type__)
        except:
            self._neo4j_feat["_id"] = None
            self._neo4j_feat["_labels"] = None
        self.match_text = d_val.get("match_text", None)
        self.match_pattern_type = d_val.get("match_pattern_type", None)

    def validate_type(self):
        var_names = self.get_var_names()
        flag = True
        if not self.__entity_def.get("D"):
            return flag

        for p in var_names:
            entity_type_def = self.__entity_def['D'].get(p) or self.__entity_def['D'].get(p + '(PK)')
            if self.__dict__.get(p, None) and entity_type_def:
                if entity_type_def == int:
                    entity_type_def_ext = (int, np.int64)
                else:
                    entity_type_def_ext = entity_type_def
                flag = flag and isinstance(self.__dict__.get(p, None), entity_type_def_ext)
        return flag

    def validate_PK(self):
        PK_value = getattr(self, self.__PK__, None)
        return PK_value is not None

    def apply_F(self):
        if self.__entity_def.get("F"):
            if not isinstance(self.__entity_def["F"], dict):
                raise TypeError(f"d_entity['F'] must be a dict type.")
            for k, v in self.__entity_def["F"].items():
                self_k = getattr(self, k, None)
                if k in self._U_fields and ObjEntity.val_is_na(self_k):  # 在只选用U_K作关系抽取时，可以避免每次对U_V中的属性查询
                    if self._init_mode == 'build_id':
                        func_exe_flag = k == self.__PK__
                    elif self._init_mode == 'query_other_fileds_in_F_by_id':
                        func_exe_flag = k != self.__PK__
                    else:  # 'build_all_fields'
                        func_exe_flag = True
                    if func_exe_flag:
                        setattr(self, k, v(*self.get_lambda_args(v)) if isinstance(v, types.LambdaType) else v)

    def get_var_names(self, ignore_startswith='__', only_fields=True):
        var_names = [var for var in self.__dict__ if not var.startswith(ignore_startswith)]
        if only_fields:
            var_names = [name for name in var_names if name in self._U_fields]
        return var_names

    def get_dict(self):
        var_names = self.fieldnames or self.get_var_names()
        return {k: v for k, v in self.__dict__.items() if k in var_names}

    def get_lambda_args(self, lambda_func):
        # 使用inspect模块来获取lambda表达式的参数名
        args = inspect.signature(lambda_func).parameters
        return [getattr(self, arg, None) for arg in args]

    def __getattr__(self, name):
        try:
            return self.__getattribute__(name)
        except AttributeError as e:
            msg = str(e) + f" for {self}!"
            raise AttributeError(msg)

    def __repr__(self):
        if self.__PK__ is None:
            repr_format = f"{self.__type__}{self.get_dict()}"
        else:
            repr_format = f"{self.__type__}_{getattr(self, self.__PK__)}"
        return repr_format


if __name__ == '__main__':
    from GH_CoRE.model.tst_case import df_tst

    tag_exid = Obj_exid.get_exid('_release_tag_exid', {"repo_id": 16563587, "tag_name": "@cockroachlabs/cluster-ui@24.3.2"})
    print(tag_exid)
    tag_exid_params = Obj_exid.get_kwargs_from_exid("_release_tag_exid", "16563587@@cockroachlabs/cluster-ui@24.3.2")
    print(tag_exid_params)

    Branch = ObjEntity("Branch")
    d_val = {'repo_id': 1}
    Branch.set_val(d_val)
    print(Branch.validate_PK())
    d_val = {'repo_id': 1, 'branch_name': 'master', 'extend_field': "xxx"}
    Branch.set_val(d_val)
    print(Branch.validate_PK())
    print(Branch.get_dict())

    Branch = ObjEntity("Branch", init_mode='build_all_fields')
    print(Branch.__dict__)
    d_val = {'_branch_exid': '1:master'}
    Branch.set_val(d_val)
    print(Branch.get_dict())

    Issue = ObjEntity("Issue")
    df_rs = df_tst
    Issue.set_val(df_rs.to_dict("records")[0])
    print(Issue.get_dict())
    print(Issue.validate_type())

    Repo = ObjEntity("Repo")
    # Repo = ObjEntity("Repo", U_init_scope=['U_K', 'U_V'])
    Repo.set_val(df_rs.to_dict("records")[1])
    print(Repo.get_dict())
    Repo._init_mode = 'build_all_fields'
    Repo.set_val(df_rs.to_dict("records")[1])
    print(Repo.validate_type(), Repo.get_dict())

    Actor = ObjEntity("Actor")
    Actor.set_val(df_rs.to_dict("records")[1])
    print(Actor.validate_type(), Actor.get_dict())

    PullRequest = ObjEntity("PullRequest")
    PullRequest.set_val(df_rs.to_dict("records")[1])
    print(PullRequest.validate_type(), PullRequest.get_dict())
