#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/11/11 3:25
# @Author : 'Lou Zehua'
# @File   : cache.py
import time
import traceback

from collections import deque
from functools import partial


class QueryCache:
    match_func = lambda x, y: x == y

    @staticmethod
    def d_match_func(params, record, feat_keys):
        is_matched = True
        try:
            params = dict(params)
            for k in feat_keys:
                feat_v = params.get(k)
                rec_v = record.get(k)
                if feat_v is None and rec_v is None:
                    pass
                else:
                    is_matched = is_matched and feat_v == rec_v
                if not is_matched:
                    break
        except Exception:
            is_matched = False
        return bool(is_matched)

    def __init__(self, max_size=100, match_func=None):
        self.cache = deque(maxlen=max_size)
        self.match_func = match_func or self.__class__.match_func
        return

    def add_record(self, record, skip_dup=True):
        if skip_dup and record in self.cache:
            return
        self.cache.append(record)
        return

    def add_records(self, records, **kwargs):
        try:
            records = list(records)
            for record in records:
                self.add_record(record, **kwargs)
        except BaseException as e:
            print(f"Nothing changed!")
            traceback.print_tb(e.__traceback__)
        return

    def get_recent_records(self):
        return self.cache

    def find_record_in_cache(self, query_feature, match_func=None):
        self.match_func = match_func or self.match_func
        res_record = None
        for cache_record in self.cache:
            if self.match_func(query_feature, cache_record):
                res_record = cache_record
                break
        return res_record


if __name__ == '__main__':
    # 使用示例
    cache = QueryCache(max_size=3)
    records = [{"label": 'a', "x": 1, "y": 1}] * 3 + [{"label": 'b', "x": 1, "y": 2}] * 2 + \
              [{"label": 'c', "x": 2, "y": 1}] * 1 + [{"label": 'd', "x": 2, "y": 2}] * 4
    print(cache, records)

    # 添加查询记录
    cache.add_records(records)

    # 获取最近的查询记录
    print(cache.get_recent_records())

    cache.match_func = partial(QueryCache.d_match_func, **{"feat_keys": ["label"]})
    print('a:', cache.find_record_in_cache({"label": 'a'}))
    print('b:', cache.find_record_in_cache({"label": 'b'}))

    # 处理不在cache中的新纪录，并添加到cache
    def get_new_record(feat_new_rec):
        time.sleep(10)
        print("Please wait...")
        new_record = dict(**dict(feat_new_rec), **{"x": 0, "y": 0})
        return new_record

    feature_new_rec = {"label": 'b'}
    new_record_cached = cache.find_record_in_cache(feature_new_rec)
    print(cache.get_recent_records())
    if new_record_cached:
        print(f"Find new record in cache: {new_record_cached}")
    else:
        new_record = get_new_record(feature_new_rec)
        cache.add_record(new_record)
    print(cache.get_recent_records())
