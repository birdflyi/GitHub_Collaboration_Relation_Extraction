#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/10/22 4:02
# @Author : 'Lou Zehua'
# @File   : ER_config.py 


event_trigger_ERE_triples_dict = {
    'IssuesEvent::action=opened': [('Issue', 'EventAction::label=OpenedBy', 'Actor'), ('Issue', 'EventAction::label=CreatedIn', 'Repo'),
                                   ('Issue', 'Reference::label=unknown', 'UnknownFromBodyRef')],
    'IssuesEvent::action=closed': [('Issue', 'EventAction::label=ClosedBy', 'Actor')],
    'IssuesEvent::action=labeled': [('Issue', 'EventAction::label=LabeledBy', 'Actor')],
    'IssuesEvent::action=reopened': [('Issue', 'EventAction::label=ReopenedBy', 'Actor')],
    'IssueCommentEvent::action=created': [('IssueComment', 'EventAction::label=OpenedBy', 'Actor'),
                                          ('IssueComment', 'EventAction::label=CommentedOnIssue', 'Issue'), ('IssueComment', 'EventAction::label=CommentedOnIssue', 'PullRequest'),
                                        ('IssueComment', 'Reference::label=unknown', 'UnknownFromBodyRef')],  # 严格的情况下，同一个事件是Issue或PullRequest之一；不严格的情况下，PullRequest被认为是一种Issue，详见https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28。 相同issue_number情况下，PullRequestEvent的issue_id与IssueCommentEvent对应的issue_id不同！可通过使用repo_id与issue_number的联合键避开类型判断
    'PullRequestEvent::action=opened': [('PullRequest', 'EventAction::label=OpenedBy', 'Actor'),
                                        ('PullRequest', 'EventAction::label=PulledRepoFrom', 'Repo::repo_id=pull_head_repo_id'),
                                        ('PullRequest', 'EventAction::label=PulledRepoTo', 'Repo'),
                                        ('PullRequest', 'EventAction::label=PulledBranchFrom', 'Branch::branch_name=pull_head_ref'),
                                        ('PullRequest', 'EventAction::label=PulledBranchTo', 'Branch::branch_name=pull_base_ref'),
                                        ('PullRequest', 'Reference::label=unknown', 'UnknownFromBodyRef')],  # unknown中PullRequest对其要解决的Issue也有知识引用
    'PullRequestEvent::action=closed&pull_merged=False': [('PullRequest', 'EventAction::label=ClosedBy', 'Actor')],  # merge时github会自动将PullRequest变为closed，若未合并关闭则可视为丢弃该分支片段。ConnectedEvent查询详见https://docs.github.com/en/graphql/reference/objects#connectedevent。
    'PullRequestEvent::action=closed&pull_merged=True': [('PullRequest', 'EventAction::label=ClosedBy', 'Actor'),
                                                         ('PullRequest', 'EventAction::label=MergedBy', 'Actor'),
                                                         ('Branch::branch_name=pull_head_ref', 'EventAction::label=MergedTo', 'Branch::branch_name=pull_base_ref'),
                                                         ('PullRequest', 'EventAction::label=MergedAs', 'Commit::commit_sha=pull_merge_commit_sha'),  # 成功merged时会同时触发一次PushEvent，因此无需初始化commit_sha之外的属性
                                                         # ('Commit::commit_sha=pull_merge_commit_sha', 'EventAction::label=PushedTo', 'Commit::commit_sha=__get_pull_base_commit_sha(PullRequest)'),  # 此关系在git log中可通过git log -1 --pretty=%P <commit-sha>查询，且已经被commit的parent记录过。__get_pull_base_commit_sha示例：getJson(https://api.github.com/repos/X-lab2017/open-digger/pulls/1292).base.sha
                                                         # ('Commit::commit_sha=pull_merge_commit_sha', 'EventAction::label=SquashedFrom', 'Commit::commit_sha=__get_PR_commits_sha_by_issue_exid(_issue_exid)[i]'),  # __get_PR_commits_sha_by_issue_exid示例：getJson(https://api.github.com/repos/X-lab2017/open-digger/pulls/1292/commits).[i].sha 实现有困难，可以用git log --oneline --graph --all --decorate或git show单独完成。
                                                         ],  # merge时github会自动将PullRequest变为closed，若未合并关闭则可视为丢弃该分支片段。ConnectedEvent暂不考虑，其查询详见https://docs.github.com/en/graphql/reference/objects#connectedevent。
    'PullRequestEvent::action=labeled': [('PullRequest', 'EventAction::label=LabeledBy', 'Actor')],
    'PullRequestEvent::action=reopened': [('PullRequest', 'EventAction::label=ReopenedBy', 'Actor')],
    'PullRequestReviewEvent::action=created': [('PullRequestReview', 'EventAction::label=CreatedBy', 'Actor'),
                                               ('PullRequestReview', 'EventAction::label=CreatedIn', 'PullRequest'),
                                               ('PullRequestReview', 'EventAction::label=ReviewedOnBranch', 'Branch::branch_name=pull_head_ref'),
                                               # ('PullRequestReview', 'EventAction::label=ReviewedOnCommit', 'Commit::commit_sha=pull_merge_commit_sha'),  # PullRequestReviewEvent中的pull_merge_commit_sha无法在github上查询出来，其对应的对象未知
                                               ('PullRequestReview', 'Reference::label=unknown', 'UnknownFromBodyRef')],
    'PullRequestReviewCommentEvent::action=created': [('PullRequestReviewComment', 'EventAction::label=CreatedBy', 'Actor'),
                                                      ('PullRequestReviewComment', 'EventAction::label=CommentedOnReview', 'PullRequestReview'),
                                                      ('PullRequestReviewComment', 'Reference::label=unknown', 'UnknownFromBodyRef')],  # platform='Gitee'无法获取PullRequestReviewComment所对应的PullRequestReview信息， github的action=created, 而gitee的action=added
    'PushEvent::action=added': [('Push', 'EventAction::label=AddedBy', 'Actor'),
                                ('Push', 'EventAction::label=AddedTo', 'Branch::branch_name=_trim_refs_heads(push_ref)'),
                                ('Push', 'EventAction::label=CommittedAs', 'Commit::commit_sha=push_head'),
                                # ('Commit::commit_sha=push_head', 'EventAction::label=CreatedBy', 'Actor::login=_for_elem_in_list(push_commits.name)'), # github中无法提供此准确连边，可以通过匹配login尽可能收集，现阶段暂时忽略
                                ('Branch::branch_name=_trim_refs_heads(push_ref)', 'EventAction::label=UpdatedWith', 'Commit::commit_sha=push_head'),  # Branch可以看作是相对动态且相对连续的Tag
                                ('Push', 'Reference::label=unknown', 'UnknownFromBodyRef')],  # Push一旦被记录为时间记录，即是必定合入分支成功的，且commit事件必定已被触发。
    'CommitCommentEvent::action=added': [('CommitComment', 'EventAction::label=AddedBy', 'Actor'),
                                         ('CommitComment', 'EventAction::label=CommentedOnCommit', 'Commit::commit_sha=commit_comment_sha'),
                                         ('CommitComment', 'Reference::label=unknown', 'UnknownFromBodyRef')],
    'ReleaseEvent::action=published': [('Release', 'EventAction::label=PublishedBy', 'Actor'),
                                       ('Release', 'EventAction::label=PublishedOnTag', 'Tag::tag_name=release_tag_name'),   # Tag的id字段与Branch有关
                                       ('Release', 'Reference::label=unknown', 'UnknownFromBodyRef')],  # ReleaseEvent::action=published事件会立即100%触发一次CreateEvent的Tag子事件
    'ForkEvent::action=added': [('Repo::repo_id=fork_forkee_id', 'EventAction::label=AddedBy', 'Actor'),
                                ('Repo::repo_id=fork_forkee_id', 'EventAction::label=OwnedBy', 'Actor::actor_id=fork_forkee_owner_id'),
                                ('Repo::repo_id=fork_forkee_id', 'EventAction::label=AddedTo', 'Repo')],  # fork_forkee_id forked from base repo_id
    'CreateEvent::action=added&create_ref_type=branch': [('Branch::branch_name=create_ref', 'EventAction::label=CreatedBy', 'Actor'),
                                                         ('Branch::branch_name=create_ref', 'EventAction::label=CreatedIn', 'Repo'),
                                                         ('Branch::branch_name=create_ref', 'EventAction::label=BasedOnBranch', 'Branch::branch_name=create_master_branch')],  # 同一个事件只能创建Tag或Branch等之一，create_ref_type可以是[branch, tag, repository]，数据库中没有repository的情况，详见 https://docs.github.com/en/rest/using-the-rest-api/github-event-types?apiVersion=2022-11-28#createevent。('actor', 'Branch::create_master_branch')划分在前置的CreateEvent事件中。
    'CreateEvent::action=added&create_ref_type=tag': [('Tag::tag_name=create_ref', 'EventAction::label=CreatedBy', 'Actor'),
                                                      ('Tag::tag_name=create_ref', 'EventAction::label=CreatedOnBranch', 'Branch::branch_name=create_master_branch'),
                                                      ('Tag::tag_name=create_ref', 'EventAction::label=CreatedOnCommit', 'Commit::commit_sha=__get_tag_commit_sha(_tag_exid, repo_name)')],  # 注意：__get_tag_commit_sha可通过GitHub GraphQL API和GitHub REST API查询
    'DeleteEvent::action=added&create_ref_type=branch': [('Branch::branch_name=delete_ref', 'EventAction::label=DeletedBy', 'Actor')],
    'DeleteEvent::action=added&create_ref_type=tag': [('Tag', 'EventAction::label=DeletedBy', 'Actor')],
    'GollumEvent::action=added': [('Gollum', 'EventAction::label=AddedBy', 'Actor'), ('Gollum', 'EventAction::label=AddedTo', 'Repo')],
    'MemberEvent::action=added': [('Actor::actor_id=member_id', 'EventAction::label=AddedBy', 'Actor'),
                                  ('Actor::actor_id=member_id', 'EventAction::label=AddedTo', 'Repo')],
    'PublicEvent::action=added': [('Repo', 'EventAction::label=MadePublicBy', 'Actor')],
    'WatchEvent::action=started': [('Repo', 'EventAction::label=StartedBy', 'Actor')],
    'IssuesReactionEvent::action=added': [('Issue', 'EventAction::label=ReceivedReactionFrom', 'Actor'), ('PullRequest', 'EventAction::label=ReceivedReactionFrom', 'Actor')]
}

# pattern
# 每条记录的类型由type::action&custom_filed字段唯一确定
# 'CreateEvent::action=added&create_ref_type=branch' 除了默认的type与action字段的判断，还有create_ref_type=branch表示自定义的字段create_ref_type值为branch的附加判断条件

"""
注意：
```plain_text
设当前upstream被合入节点的commit sha码为：0432ecb

PR API的JSON中字段：
{
    merged_by： m 合并者
    user: pa 是PullRequest的发起者
    head.sha: ac7f1f5 是贡献者origin下游github仓库的head所指向的commit sha码
    base.sha: 0432ecb 是upstream上游github仓库的被合入点所指向的commit sha码
}

其中贡献者origin下游github仓库的更改包含(由父节点到子节点排序)
[
    eb6ee0f
    4182dc7
    ac7f1f5
]

最终PR merged完成时，会产生一个upstream项目中的新提交：89fbf79(clickhouse数据库中push_head字段即为此值)

即在origin中：
0432ecb(PR API base) -> [eb6ee0f -> 4182dc7 -> ac7f1f5(PR API head)]
在upstream中：
0432ecb -> 89fbf79(clickhouse PushEvent.push_head, PullRequestEvent.pull_merge_commit_sha)
```
"""

# 概念模型的实体类型集
EC = {
    'Actor',
    'Branch',
    'Commit',
    'CommitComment',
    'Gollum',
    'Issue',
    'IssueComment',
    # 'IssuesReaction',
    # 'Public'
    'PullRequest',
    'PullRequestReview',
    'PullRequestReviewComment',
    'Push',
    'Release',
    'Repo',
    'Tag'
}

# 每个实体类型的关键码
EC_PK = {
    'Actor': 'actor_id',  # 识别文本示例：@{actor_login} or /{actor_login}
    'Branch': '_branch_exid',  # 需要用它连接PullRequest与commit，识别文本示例：/{_repo_full_name}/tree/{branch_name}
    'Commit': 'commit_sha',
    # 识别文本示例：/{_repo_full_name}/commit/{commit_sha} or /{_repo_full_name}/pull/{issue_number}/commits/{commit_sha}，验证存在后的{commit_sha} or {commit_sha[:7]}
    'CommitComment': 'commit_comment_id',
    # 识别文本示例：/{_repo_full_name}/commit/{commit_sha}#commitcomment-{commit_comment_id}
    'Gollum': '_gollum_exid',  # 识别文本示例：/{_repo_full_name}/wiki
    'Issue': '_issue_exid',  # 为了与拥有多个issue_id的PullRequest统一，使用{repo_id}#{issue_number}模式作为主键，
    #  # 识别文本示例：/{_repo_full_name}/issues/{issue_number} or /{_repo_full_name}/issues/{issue_number}#issue-{issue_id} or
    #  # /{_repo_full_name}#{issue_number} or #{issue_number} or [Ii]ssue#{issue_number}
    'IssueComment': 'issue_comment_id',
    # 识别文本示例：/{_repo_full_name}/(?:issues|pull)/{issue_number}#issuecomment-{issue_comment_id}
    # 'IssuesReaction': None,  # 识别文本示例: 无
    # 'Public': None,  # 识别文本示例: 无
    'PullRequest': '_issue_exid',
    # 识别文本示例：Issue的所有识别方式 or /{_repo_full_name}/pull/{issue_number} or /{_repo_full_name}/pull/{issue_number}#issue-{issue_id}
    'PullRequestReview': 'pull_review_id',
    # 识别文本示例：/{_repo_full_name}/(?:issues|pull)/{issue_number}#pullrequestreview-{pull_review_id}
    'PullRequestReviewComment': 'pull_review_comment_id',
    # 识别文本示例：/{_repo_full_name}/(?:issues|pull)/{issue_number}/files#r{pull_review_comment_id}
    #  # or /{_repo_full_name}/(?:issues|pull)/{issue_number}/files/{push_head}#r{pull_review_comment_id} or
    #  # /{_repo_full_name}/(?:issues|pull)/{issue_number}#discussion_r{pull_review_comment_id}
    'Push': 'push_id',  # 需要用它连接PullRequest与commit，识别文本示例: 无
    'Release': 'release_id',  # 识别文本示例: /{_repo_full_name}/releases/tag/{release_tag_name}
    'Repo': 'repo_id',  # 识别文本示例: /{_repo_full_name}
    'Tag': '_tag_exid',  # 需要用它连接release与commit，识别文本示例: 与Branch相同/{_repo_full_name}/tree/{tag_name}
}
