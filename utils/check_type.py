#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2023/5/23 1:38
# @Author : 'Lou Zehua'
# @File   : check_type.py

def is_number(s, nan_as_true=False):
    try:
        float_s = float(s)
        if nan_as_true:
            return True
        elif float_s == float_s:  # filter nan
            return True
        else:
            return False
    except TypeError or ValueError:
        return False


def is_list(x, nan_as_true=False, use_eval=False):
    flag = type(x) is list
    if nan_as_true:
        flag = flag or is_nan(x)
    if use_eval and type(x) is str:
        flag = str(x).startswith('[') and str(x).endswith(']')
    return flag


def is_str(x, nan_as_true=False):
    flag = type(x) is str
    if nan_as_true:
        flag = flag or is_nan(x)
    return flag


def is_nan(s):
    s = str(s)
    if s.lower() == 'nan':
        return True
    else:
        try:
            float_s = float(s)
        except ValueError:
            return False
        return float_s != float_s


def is_na(s, check_str_eval=True):
    if is_nan(s):
        return True
    try:
        if check_str_eval and type(s) == str:
            if len(s):
                s = eval(s)  # True: [np.nan, '', [], (), {}, np.array([]), pd.DataFrame(), '[]', '()', '{}']
        if not len(s):
            return True
    except ValueError:
        pass
    return False


if __name__ == '__main__':
    import numpy as np
    import pandas as pd

    empty_list = [np.nan, 'NaN', 'nan', '', [], (), {}, np.array([]), pd.DataFrame(), '[]', '()', '{}']
    empty_series = pd.Series(data=empty_list)
    print("data:")
    print(pd.DataFrame(data=[empty_series.apply(str), empty_series.apply(type)]).T)
    print("is_nan:")
    print(empty_series.apply(is_nan))
    print("is_na:")
    print(empty_series.apply(is_na))
