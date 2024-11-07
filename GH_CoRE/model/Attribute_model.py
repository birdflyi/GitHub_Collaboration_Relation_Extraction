#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/10/22 22:48
# @Author : 'Lou Zehua'
# @File   : Attribute_model.py

# 实体型Entity Type：E(U, D, F)，其中E为实体名，U为组成该实体概念的属性名集合，D为属性组U中属性所来自的域，F为属性间数据的依赖关系集合。

from enum import Enum, unique


class EnumExt(Enum):
    def __new__(cls, value, display_name=None):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.display_name = display_name
        return obj

    def __init__(self, *args):
        self.display_name = self.display_name or self.name

    @staticmethod
    def get_name_by_display_name(cls, display_name):
        for name, member in cls.__members__.items():
            if member.display_name == display_name:
                return name
        raise ValueError(f"No member with display_name {display_name}")

    @staticmethod
    def get_enum_obj_by_temp_name(cls, temp_name):
        name = temp_name if temp_name in cls.__dict__.keys() else EnumExt.get_name_by_display_name(cls, temp_name)
        enum_obj = cls[name]
        return enum_obj


@unique
class Platform(EnumExt):
    GitHub = 1
    Gitee = 2
    AtomGit = 3
    GitLab_com = (4, "GitLab.com")  # GitLab.com
    Gitea = 5
    GitLab_cn = (6, "GitLab.cn")  # GitLab.cn


@unique
class EventType(Enum):
    CommitCommentEvent = 1
    CreateEvent = 2
    DeleteEvent = 3
    ForkEvent = 4
    GollumEvent = 5
    IssueCommentEvent = 6
    IssuesEvent = 7
    MemberEvent = 8
    PublicEvent = 9
    PullRequestEvent = 10
    PullRequestReviewCommentEvent = 11
    PushEvent = 12
    ReleaseEvent = 13
    WatchEvent = 14
    PullRequestReviewEvent = 15
    IssuesReactionEvent = 16
    IssueCommentsReactionEvent = 17
    LabelEvent = 18
    ReactionPlaceholderEvent = 126
    LabelPlaceholderEvent = 127


@unique
class Action(Enum):
    added = 1
    closed = 2
    created = 3
    labeled = 4
    opened = 5
    published = 6
    reopened = 7
    started = 8


@unique
class AuthorType(Enum):
    Bot = 1
    Mannequin = 2
    Organization = 3
    User = 4


@unique
class AuthorAssociation(Enum):
    COLLABORATOR = 1
    CONTRIBUTOR = 2
    MEMBER = 3
    NONE = 4
    OWNER = 5
    MANNEQUIN = 6


@unique
class PullReviewState(Enum):
    approved = 1
    commented = 2
    dismissed = 3
    changes_requested = 4
    pending = 5


@unique
class PusherType(Enum):
    deploy_key = 1
    user = 2


@unique
class CreateRefType(Enum):
    branch = 1
    tag = 2


if __name__ == '__main__':
    print(Platform.GitLab_com.value, Platform.GitLab_com.name, Platform.GitLab_com.display_name)
    enum_obj = EnumExt.get_enum_obj_by_temp_name(Platform, 'GitLab.com')
    print(enum_obj.value, enum_obj.name, enum_obj.display_name)
    enum_obj = EnumExt.get_enum_obj_by_temp_name(CreateRefType, 'branch')
    print(enum_obj.value, enum_obj.name)
