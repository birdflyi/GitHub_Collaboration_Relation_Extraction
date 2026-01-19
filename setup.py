#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/11/7 8:02
# @Author : 'Lou Zehua'
# @File   : setup.py
import re

from setuptools import setup, find_packages
from pkg_resources import parse_requirements

with open("./requirements.txt", encoding="utf-8") as fp:
    install_requires = [str(requirement) for requirement in parse_requirements(fp)]

with open("README.md", "r", encoding="utf-8") as fp:
    long_description = fp.read()

with open("./GH_CoRE/__init__.py", encoding="utf-8") as fp:
    content = fp.read()
    versions = re.findall(r'(?<=\s__version__ = ")\d[-_0-9a-zA-Z\.]*', content)

setup(name="gh_core",
      version=versions[0],
      author="birdflyi",
      author_email="zhlou@stu.ecnu.edu.cn",
      description="GitHub Collaboration Relation Extraction",
      long_description=long_description,
      long_description_content_type="text/markdown",
      url="https://github.com/birdflyi/GitHub_Collaboration_Relation_Extraction",
      project_urls={
          "Repository": "https://github.com/birdflyi/GitHub_Collaboration_Relation_Extraction.git",
      },
      license="Apache-2.0",  # [SPDX](https://packaging.python.org/en/latest/glossary/#term-License-Expression)
      classifiers=[
            # Development Status, see https://pypi.org/classifiers/
            #   3 - Alpha
            #   4 - Beta
            #   5 - Production/Stable
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Developers",
            "Intended Audience :: Science/Research",
            "License :: OSI Approved :: Apache Software License",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Topic :: Scientific/Engineering :: Information Analysis",
      ],
      packages=find_packages(exclude=["etc"]),
      python_requires=">=3.9, <3.12",
      keywords=["Relation Extraction", "GitHub event", "dataset"],
      install_requires=install_requires,
      include_package_data=True,
      zip_safe=False,
      options={
              'bdist_wheel': {
                  'universal': True,
              }
          }
      )
