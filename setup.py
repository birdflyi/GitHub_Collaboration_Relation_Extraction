#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/11/7 8:02
# @Author : 'Lou Zehua'
# @File   : setup.py 

import GH_CoRE

from setuptools import setup, find_packages
from pkg_resources import parse_requirements

with open("./requirements.txt", encoding="utf-8") as fp:
    install_requires = [str(requirement) for requirement in parse_requirements(fp)]

setup(name=GH_CoRE.__name__,
      version=GH_CoRE.__version__,
      description='GitHub Collaboration Relation Extraction',
      url='https://github.com/birdflyi/GitHub_Collaboration_Relation_Extraction',
      author='birdflyi',
      author_email='zhlou@stu.ecnu.edu.cn',
      license="Apache License 2.0",
      platforms='any',
      classifiers=[
            # Development Status, see https://gist.github.com/nazrulworld/3800c84e28dc464b2b30cec8bc1287fc
            #   3 - Alpha
            #   4 - Beta
            #   5 - Production/Stable
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'Intended Audience :: System Administrators',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: Apache Software License',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Topic :: Scientific/Engineering :: Information Analysis',
      ],
      keywords='Relation Extraction',
      packages=find_packages(exclude=["etc"]),
      install_requires=install_requires,
      python_requires='>=3.6',
      )
