#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/10/24 7:10
# @Author : 'Lou Zehua'
# @File   : Relation_model.py

import re

import pandas as pd

from GH_CoRE.model.ER_config_parser import df_ref_tuples_raw, df_ref_tuples, event_trim_subType


def get_relation_label_repr(rec):
    d_rec = dict(rec)
    re_relation_label_group = re.findall(r'(?<=::label=)([_0-9a-zA-Z]+)', d_rec["relation_label"])
    if "source_node_type" not in d_rec.keys():
        d_rec["source_node_type"] = event_trim_subType(d_rec["source_node_label"])
    if "target_node_type" not in d_rec.keys():
        d_rec["target_node_type"] = event_trim_subType(d_rec["target_node_label"])
    relation_label_repr = d_rec["source_node_type"] + '_' + (
        re_relation_label_group[0] if re_relation_label_group else "unknown") + "_" + d_rec["target_node_type"]
    return relation_label_repr


def get_relation_type(rec):
    re_relation_type_group = re.findall(r'([_0-9a-zA-Z]+)(?=::)', rec["relation_label"])
    relation_type = re_relation_type_group[0] if re_relation_type_group else "unknown"
    return relation_type


class Relation:
    df_relation_type = pd.DataFrame()
    df_ref_tuples["relation_label"] = df_ref_tuples_raw["relation_label"]
    df_relation_type['relation_label_repr'] = pd.DataFrame(df_ref_tuples).apply(get_relation_label_repr, axis=1)
    df_relation_type['relation_type'] = pd.DataFrame(df_ref_tuples_raw).apply(get_relation_type, axis=1)
    df_relation_type_unique = df_relation_type.drop_duplicates(subset='relation_label_repr', keep='first')
    df_relation_type_unique = df_relation_type_unique.reset_index().rename(columns={"index": "relation_label_id"})

    def __init__(self, relation_label_id=None, relation_label_repr=None):
        self.relation_label_id = None
        self.relation_type = None
        self.relation_label_repr = None
        if relation_label_id is not None:
            self.relation_label_id = relation_label_id
            self.set_relation_type(by='id')  # 已尝试初始化self.relation_label_repr
            if self.relation_label_repr:
                if relation_label_repr is not None and self.relation_label_repr != relation_label_repr:
                    print(
                        f"The relation_label_repr doesnot matched with Relation.df_relation_type_unique! It will be covered by the record with relation_label_id {self.relation_label_id}!")
        elif relation_label_repr is not None:
            self.relation_label_repr = relation_label_repr
            self.set_relation_type(by='repr')
        else:
            raise ValueError("relation_label_id and relation_label_repr cannot be None at the same time!")
        return

    def set_relation_type(self, by='id'):
        if by == 'id':
            k_colname = f'relation_label_id'
        elif by == 'repr':
            k_colname = f'relation_label_repr'
        else:
            raise ValueError("The variable by must be in ['id', 'repr']!")
        rec_query = Relation.df_relation_type_unique[
            Relation.df_relation_type_unique[k_colname] == getattr(self, k_colname, None)]
        if len(rec_query):
            self.relation_label_id = rec_query["relation_label_id"].values[0]
            self.relation_type = rec_query["relation_type"].values[0]
            self.relation_label_repr = rec_query["relation_label_repr"].values[0]
        return None

    def get_dict(self):
        return self.__dict__

    def __repr__(self):
        return self.relation_type + "::" + self.relation_label_repr + "#" + str(self.relation_label_id) or ''


if __name__ == '__main__':
    print(Relation.df_relation_type_unique)
    print(Relation(relation_label_repr="Issue_OpenedBy_Actor").get_dict())
