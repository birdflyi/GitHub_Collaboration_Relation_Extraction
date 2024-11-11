#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2023/4/19 21:15
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
pkg_rootdir = os.path.dirname(cur_dir)  # os.path.dirname()向上一级，注意要对应工程root路径
if pkg_rootdir not in sys.path:  # 解决ipynb引用上层路径中的模块时的ModuleNotFoundError问题
    sys.path.append(pkg_rootdir)
    print('-- Add root directory "{}" to system path.'.format(pkg_rootdir))

__all__ = [
    "logUtils",  # sub-package needs to be imported and to extend __all__
    # file in this package just list out
    "cache",
    "check_type",
    "conndb",
    "prepare_sql",
    "request_api",
]

from GH_CoRE.utils import logUtils  # sub-package needs to be imported and to extend __all__
from GH_CoRE.utils.cache import *
from GH_CoRE.utils.check_type import *
from GH_CoRE.utils.conndb import *
from GH_CoRE.utils.prepare_sql import *
from GH_CoRE.utils.request_api import *

# sub-package needs to be imported and to extend __all__
__all__.extend(logUtils.__all__)
