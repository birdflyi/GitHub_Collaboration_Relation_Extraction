#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/11/7 8:02
# @Author : 'Lou Zehua'
# @File   : setup.py
import re

import GH_CoRE

from setuptools import setup, find_packages
from pkg_resources import parse_requirements

with open("./requirements.txt", encoding="utf-8") as fp:
    install_requires = [str(requirement) for requirement in parse_requirements(fp)]

with open("./pyproject.toml", encoding="utf-8") as fp:
    content = fp.read()
    names = re.findall(r'(?<=\nname = ")[A-Za-z0-9][-_0-9a-zA-Z\.]*', content)
    versions = re.findall(r'(?<=\nversion = ")\d[-_0-9a-zA-Z\.]*', content)

name = names[0] if names else GH_CoRE.__name__
version = versions[0] if versions else GH_CoRE.__version__

setup(name=name,
      version=version,
      description='GitHub Collaboration Relation Extraction',
      url='https://github.com/birdflyi/GitHub_Collaboration_Relation_Extraction',
      license="Apache License 2.0",
      platforms='any',
      classifiers=[
            # Development Status, see https://pypi.org/classifiers/
            #   3 - Alpha
            #   4 - Beta
            #   5 - Production/Stable
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: Apache Software License',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Topic :: Scientific/Engineering :: Information Analysis',
      ],
      packages=find_packages(exclude=["etc"]),
      install_requires=install_requires,
      )
