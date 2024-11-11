#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/10/24 17:41
# @Author : 'Lou Zehua'
# @File   : Relation_extraction.py

import copy
import os
from functools import partial

import pandas as pd

from GH_CoRE.model.Attribute_getter import _get_field_from_db
from GH_CoRE.model.ER_config_parser import eventType_params2repr, match_substr__from_body, df_ref_tuples_raw, \
    eventType_params
from GH_CoRE.model.Entity_model import ObjEntity
from GH_CoRE.model.Entity_recognition import get_df_bodyRegLinks_eachLinkPatType
from GH_CoRE.model.Entity_search import get_ent_obj_in_link_text
from GH_CoRE.model.Event_model import Event
from GH_CoRE.model.Relation_model import Relation, get_relation_label_repr
from GH_CoRE.utils.cache import QueryCache


def get_df_and_dict_format_record(record):
    df_record = pd.DataFrame()
    d_record = {}
    try:
        if isinstance(record, pd.DataFrame):
            df_record = copy.deepcopy(record)
            d_record = record.to_dict("records")[0]
        elif isinstance(record, pd.Series):
            df_record = record.to_frame().T
            d_record = record.to_dict()
        elif isinstance(record, dict):
            df_record = pd.DataFrame(data=[record])
            d_record = record
        else:
            raise TypeError("The type of record should be in [pandas.DataFrame, pandas.Series, dict].")
    except BaseException:
        pass
    return df_record, d_record


def match_eventType_params_with_record(eventType_params_patterns, record):
    if isinstance(record, pd.DataFrame):
        record = record.to_dict("records")[0]
    record = dict(record)
    matched_pattern = None
    for eventType_params_pattern in eventType_params_patterns:
        if record['type'] == eventType_params_pattern[0]:
            if len(eventType_params_pattern) == 1:
                matched_pattern = eventType_params_pattern
                break
            else:
                conditions_flag = True
                # all eventType_params_pattern[1][key] matched with record[key]
                for k, v in eventType_params_pattern[1].items():
                    is_matched = (v == record.get(k, None))
                    if v in ['True', 'False']:
                        is_matched = is_matched or (eval(v) == record.get(k))
                    conditions_flag = conditions_flag and is_matched
                if conditions_flag:
                    matched_pattern = eventType_params_pattern
                    break
    return matched_pattern


def get_obj_collaboration_tuples_from_record(record, extract_mode=3, cache=None):
    if cache is None:
        cache = QueryCache(max_size=200)
        cache.match_func = partial(QueryCache.d_match_func, **{"feat_keys": ["link_pattern_type", "link_text", "rec_repo_id"]})
    obj_collaboration_tuple_list = []
    df_record, d_record = get_df_and_dict_format_record(record)
    if not len(df_record):
        return obj_collaboration_tuple_list

    # The 'extract_mode' should be in [0, 1, 2, 3]
    extract_ref_from_event, extract_ref_from_bodylink = bool(extract_mode & 0x2), bool(extract_mode & 0x1)

    # 匹配record的Event type
    matched_eventType_params = match_eventType_params_with_record(eventType_params, d_record)
    matched_eventType_params_repr = eventType_params2repr(matched_eventType_params[0], matched_eventType_params[1])
    # 获得Event type的三元组模式
    df_matched_ref_pattern = df_ref_tuples_raw[df_ref_tuples_raw['event_trigger'] == matched_eventType_params_repr]
    # 构建元组
    for matched_ref_pattern_dict in df_matched_ref_pattern.to_dict("records"):
        src_nt = matched_ref_pattern_dict["source_node_label"]
        tar_nt = matched_ref_pattern_dict["target_node_label"]
        match_src_nt_from_body = match_substr__from_body(src_nt)  # src_nt包含子串"from_body"标志
        match_tar_nt_from_body = match_substr__from_body(tar_nt)  # tar_nt包含子串"from_body"标志
        relation_label_repr = get_relation_label_repr(matched_ref_pattern_dict)
        relation = Relation(relation_label_repr=relation_label_repr)
        event = Event(event_id=d_record.get('id'), event_trigger=matched_ref_pattern_dict['event_trigger'],
                      event_time=d_record.get('created_at'))
        if not match_src_nt_from_body and not match_tar_nt_from_body:
            if extract_ref_from_event:
                # Entity Search
                src_nt_obj = ObjEntity(src_nt)
                src_nt_obj.set_val(d_record)
                if src_nt_obj.__PK__ not in d_record.keys():
                    d_record[src_nt_obj.__PK__] = getattr(src_nt_obj, src_nt_obj.__PK__)
                tar_nt_obj = ObjEntity(tar_nt)
                tar_nt_obj.set_val(d_record)
                if not src_nt_obj.validate_PK() or not tar_nt_obj.validate_PK():
                    where_param = {"platform": 'GitHub', "id": event.event_id, "type": event.event_type}
                    df_record_query = _get_field_from_db('*', where_param, dataframe_format=True)
                    if len(df_record_query):
                        df_record, d_record = get_df_and_dict_format_record(df_record_query)
                        src_nt_obj.set_val(d_record)
                        tar_nt_obj.set_val(d_record)
                temp_obj_collaboration_tuple = (src_nt_obj, tar_nt_obj, relation, event)
                obj_collaboration_tuple_list.append(temp_obj_collaboration_tuple)
            else:
                pass
        elif not match_src_nt_from_body and match_tar_nt_from_body:  # body中link所对应的三元组
            if extract_ref_from_bodylink:
                # Entity Search
                nt_from_fileds = src_nt if not match_src_nt_from_body else tar_nt
                nt_from_body = src_nt if match_src_nt_from_body else tar_nt
                obj_nt_from_fileds = ObjEntity(nt_from_fileds)
                obj_nt_from_fileds.set_val(d_record)
                if not obj_nt_from_fileds.validate_PK():
                    where_param = {"platform": 'GitHub', "id": event.event_id, "type": event.event_type}
                    df_record_query = _get_field_from_db('*', where_param, dataframe_format=True)
                    if len(df_record_query):
                        df_record, d_record = get_df_and_dict_format_record(df_record_query)
                        obj_nt_from_fileds.set_val(d_record)
                # 构建实体字典
                # NER: 从body中抽取出link
                df_bodyRegLinks_eachLinkPatType = get_df_bodyRegLinks_eachLinkPatType(df_record)
                if len(df_bodyRegLinks_eachLinkPatType):
                    linkPatType_body_regexed_links_dict = df_bodyRegLinks_eachLinkPatType.to_dict('records')[0]
                    # 如何与正则匹配结合将类型nt和record查到
                    for link_pattern_type, body_regexed_links in linkPatType_body_regexed_links_dict.items():
                        if isinstance(body_regexed_links, list):  # 此record的body匹配到的link列表，否则只能是pd.isna
                            for link_text in body_regexed_links:
                                # Entity Search
                                feature_new_rec = {"link_pattern_type": link_pattern_type, "link_text": link_text, "rec_repo_id": d_record.get("repo_id")}
                                new_record_cached = cache.find_record_in_cache(feature_new_rec)
                                if new_record_cached:
                                    # print(f"find new record in cache: {new_record_cached}")
                                    obj_nt_from_body = dict(new_record_cached).get("obj_nt_from_body", ObjEntity("Obj"))
                                else:
                                    obj_nt_from_body = get_ent_obj_in_link_text(link_pattern_type, link_text, d_record)
                                    new_record = dict(**feature_new_rec, **{"obj_nt_from_body": obj_nt_from_body})
                                    cache.add_record(new_record)

                                objnt_prop_dict = obj_nt_from_body.get_dict().get("objnt_prop_dict", None)
                                duplicate_matching = False
                                if objnt_prop_dict:
                                    objnt_prop_dict = dict(objnt_prop_dict)
                                    duplicate_matching = objnt_prop_dict.get("duplicate_matching", False)
                                if not duplicate_matching:
                                    if not match_src_nt_from_body:
                                        temp_obj_collaboration_tuple = (obj_nt_from_fileds, obj_nt_from_body, relation, event)
                                    else:
                                        temp_obj_collaboration_tuple = (obj_nt_from_body, obj_nt_from_fileds, relation, event)
                                    obj_collaboration_tuple_list.append(temp_obj_collaboration_tuple)
                        else:  # pd.isna
                            pass
            else:
                pass
        else:
            raise TypeError(
                "The source_node_label and target_node_label in the 'df_ref_tuples_raw' shouldnot be related to body links at the same time." \
                "Try using Event entities to resolve the relationships between them.")
    return obj_collaboration_tuple_list, cache


# set extend_field=True if the uncertain type object links need to be saved.
def get_df_collaboration(obj_collaboration_tuple_list, extend_field=True):
    columns = ["src_entity_id", "src_entity_type", "tar_entity_id", "tar_entity_type", "relation_label_id",
               "relation_type", "relation_label_repr", "event_id", "event_trigger", "event_type", "event_time"]
    columns_extend_field = ["tar_entity_match_text", "tar_entity_match_pattern_type", "tar_entity_objnt_prop_dict"]
    if extend_field:
        columns = columns + columns_extend_field
    df_collaboration = pd.DataFrame(columns=columns)
    for obj_collaboration_tuple in obj_collaboration_tuple_list:
        src_entity, tar_entity, relation, event = obj_collaboration_tuple[:4]
        new_row = {
            "src_entity_id": getattr(src_entity, src_entity.__PK__, None) if src_entity.__PK__ else None,
            "src_entity_type": src_entity.__type__,
            "tar_entity_id": getattr(tar_entity, tar_entity.__PK__, None) if tar_entity.__PK__ else None,
            "tar_entity_type": tar_entity.__type__,
            "relation_label_id": relation.relation_label_id, "relation_type": relation.relation_type,
            "relation_label_repr": relation.relation_label_repr,
            "event_id": event.event_id, "event_trigger": event.event_trigger, "event_type": event.event_type,
            "event_time": event.event_time.strftime('%Y-%m-%d %H:%M:%S') if isinstance(event.event_time, pd.Timestamp) else event.event_time
        }
        if extend_field:  # only target entity can be referenced with text
            new_row["tar_entity_match_text"] = getattr(tar_entity, "match_text", None)
            new_row["tar_entity_match_pattern_type"] = getattr(tar_entity, "match_pattern_type", None)
            new_row["tar_entity_objnt_prop_dict"] = getattr(tar_entity, "objnt_prop_dict", None)
        df_collaboration.loc[len(df_collaboration)] = new_row  # 添加新记录
    return df_collaboration


def save_GitHub_Collaboration_Network(df_collaboration, save_path, add_mode_if_exists=False,
                                      make_dir_if_not_exist=True):
    if make_dir_if_not_exist:
        dir_path = os.path.dirname(save_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
    if add_mode_if_exists:
        if not os.path.exists(save_path):
            df_collaboration.to_csv(save_path, mode='w', header=True, index=False)
        else:
            df_collaboration.to_csv(save_path, mode='a', header=False, index=False)  # 追加模式
    else:
        df_collaboration.to_csv(save_path, mode='w', header=True, index=False)
    return None


if __name__ == '__main__':
    from etc import filePathConf
    from GH_CoRE.model.tst_case import df_tst

    print(get_obj_collaboration_tuples_from_record(df_tst.to_dict("records")[1]))

    d_rec = {
        "id": 27901170588,
        # "actor_login": "Zzzzzhuzhiwei",
        # "repo_id": 288431943,
        # "repo_name": "X-lab2017/open-digger",
        # "issue_number": "1238",
        # "issue_title": "OpenDigger Biweekly Meetings, 2022-2023 Spring Term",
        "type": "IssuesEvent",
        "action": "opened",
        # "created_at": Timestamp("2023-03-22 14:03:48"),
        # "body": "",
        # 'push_commits.message': "",
        # "release_body": "",
    }
    # match_eventType_params_with_record(eventType_params, d_rec)
    cache = None
    obj_collaboration_tuple_list, cache = get_obj_collaboration_tuples_from_record(d_rec, cache=cache)
    print(obj_collaboration_tuple_list)
    pd.set_option('display.max_columns', None)
    df_collaboration = get_df_collaboration(obj_collaboration_tuple_list, extend_field=True)
    print(df_collaboration)
    save_path = os.path.join(filePathConf.absPathDict[filePathConf.GITHUB_OSDB_DATA_DIR], 'GitHub_Collaboration_Network_repos/test.csv')
    save_GitHub_Collaboration_Network(df_collaboration, save_path=save_path, add_mode_if_exists=False)
