#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2023/4/19 21:16
# @Author : 'Lou Zehua'
# @File   : __init__.py

import os
import sys

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

__all__ = [
    "model",  # sub-package needs to be imported and to extend __all__
    "working_flow",  # sub-package needs to be imported and to extend __all__
    "utils",  # sub-package needs to be imported and to extend __all__
    "data_dict_settings",  # file in this package just list out
    # var or func/module in other file needs to be imported from file
    "columns_full",
    "columns_simple",
    "body_columns_dict",
    "event_columns_dict",
    "re_ref_patterns",
    "USE_RAW_STR",
    "USE_REG_SUB_STRS",
    "USE_REG_SUB_STRS_LEN",
    "use_data_confs",
    "default_use_data_conf"
]

# sub-package needs to be imported and to extend __all__
from GH_CoRE import model, working_flow, utils

from GH_CoRE.data_dict_settings import columns_full, columns_simple, body_columns_dict, event_columns_dict, \
    re_ref_patterns, USE_RAW_STR, USE_REG_SUB_STRS, USE_REG_SUB_STRS_LEN, use_data_confs, default_use_data_conf

__all__.extend(model.__all__)
__all__.extend(working_flow.__all__)
__all__.extend(utils.__all__)

__version__ = "1.2.1"
