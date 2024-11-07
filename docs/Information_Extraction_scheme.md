# 2. 信息抽取

## 2.1 常见任务[1,2,3]

### 2.1.1 实体识别

命名实体识别即用正则表达式识别出body中的实体字符串，实体搜索即用实体字符串匹配参与事件的实体对象。

参与事件的实体类型有：
```
  EC = 
    {
      'Actor',
      'Branch',
      'Commit',
      'CommitComment',
      'Gollum',
      'Issue',
      'IssueComment',
      # 'IssuesReaction',
      # 'Public',
      'PullRequest',
      'PullRequestReview',
      'PullRequestReviewComment',
      'Push',
      'Release',
      'Repo',
      'Tag'
    }
```
其中主要的实体类型包括Actor(Information as process: BecomingInformed)、Issue_PR(Information as Knowledge)、Repo(Information as thing: Data, Document)、Commit(Information processing: Data processing)[4,5,6]，对应的信息的各方面象限图位置依次为三、二、一、四，见Four_aspects_of_information__Information_as_thing.png。Issue_PR指Issue和PullRequest两种类型。与主要实体类型相关的关系可以用来推荐参与者discuss Topics、推荐贡献者open Issue&PR、推荐使用者watch&fork Repo、推荐评审者review Commits等.

![Four_aspects_of_information__Information_as_thing.png](../docs/Four_aspects_of_information__Information_as_thing.png)

### 2.1.2 关系抽取

关系(Relation)：即参与事件的实体之间的连边，按照表现形式划分有EventAction和Reference两种类别。

| 场景\实体 | Actor | Issue_PR | Repo | Commit |
|----|----|----|----|----|
| 情境共现（场景特征） | Actor(事件共被引及共引) | Issue_PR(事件共被引及共引) | Repo(事件共被引及共引) | Commit(共同tag和release及同根的branch) |
| 信息传递（内容重用） | Actor(assign和@-mention) | Issue_PR(协作时comment文本或语义引用) | Repo(prmerge和submodule) | Commit(与特定组件相关的commit之间的更新关系) |
| 资源依赖（上下游实体依赖） | Actor(member和follow) | Issue_PR(创建时connection、body依存引用) | Repo(fork和import) | Commit(合并时的parents sha) |

主要抽取与Issue相关的引用关系(目标是为了**用引用网络促进知识传播，进而促进技术生产力**，详见[选择目标话题](https://shimo.im/docs/1d3aMv5VrzU06R3g#anchor-2OJV))。

### 2.1.3 事件抽取

事件触发词选用事件记录的type与action的组合；~~事件论元选取主体、客体、时间、地点；~~事件属性选取倾向性。

## 2.2 事件示例

示例："[Zzzzzhuzhiwei](https://github.com/Zzzzzhuzhiwei)(Actor) 在 [X-lab2017/open-digger](https://github.com/X-lab2017/open-digger)(Repo) 下 创建 [#1238](https://github.com/X-lab2017/open-digger/issues/1238)(Issue)，其中提及了[@xgdyp](https://github.com/xgdyp)(Actor), [#1237](https://github.com/X-lab2017/open-digger/issues/1237)(Issue)，创建时间 2023-03-22 14:03:48(DateTime)"。

以下分析过程中使用记号如下：
{
  "actor1": "Zzzzzhuzhiwei",
  "actor2": "xgdyp",
  "repo1": "X-lab2017/open-digger",
  "issue1": "#1238",
  "issue2": "#1237",
  "time1": "2023-03-22 14:03:48",
 }

- 事件分析：
  - 1. 选用E-R模型描述事件中的实体之间关系。
  - 2. 信息模式定义：
    - 2.1 定义概念模型的实体类别，关键码，实体型；
    - 2.2 定义关系模式的关系类别，候选码，关系模式；
  - 3. 应用
  
- 实体识别：
  - 概念模型的实体类型集EC = {Actor, Repo, Issue}
  - 每个实体类型的关键码 EC_PK = {Actor: actor_id, Repo: repo_id, Issue: issue_id}
  - 实体型Entity Type：E(U, D, F)，其中E为实体名，U为组成该实体概念的属性名集合，D为属性组U中属性所来自的域，F为属性间数据的依赖关系集合。
    - E: Actor
      - U_K = {actor_id(PK), actor_login}  # PK表示关键码，以_开头表示需要在clickhouse数据库已有属性的基础上进一步处理，以__开头表示需要使用GitHub REST API或GitHub GraphQL API。actor_login在快照时刻具有唯一性，同样可作为快照key。
      - U_V = None  # clickhouse中可查属性{issue_author_type, issue_comment_author_type, pull_merged_by_type, pull_requested_reviewer_type, pull_review_comment_author_type, fork_forkee_owner_type, delete_pusher_type, create_pusher_type, member_type, release_author_type, commit_comment_author_type}；此外需要从GitHub REST API获取的额外属性{type, html_url, followers_url, following_url, gists_url, starred_url, subscriptions_url, organizations_url, repos_url, events_url, received_events_url, name, company, blog, email, public_repos, public_gists, followers, following}, 其中除delete_pusher_type与create_pusher_type外，其他actor type取值类型ActorType = Enum8('Bot' = 1, 'Mannequin' = 2, 'Organization' = 3, 'User' = 4), API示例https://api.github.com/users/ClickHouse 或 https://api.github.com/user/54801242
      - D = {actor_id(PK) int, actor_login string(39)}
      - F = None
    - E: Issue
      - U_K = {_issue_exid(PK), issue_id, repo_id, issue_number, issue_author_id}
      - U_V = {issue_title, body}  # issue_title, body需去重（action = closed reopened labeled冗余，可只取opened），clickhouse可查属性{actor_id, actor_login, repo_name, org_id, org_login, created_at, issue_labels.name, issue_labels.default, issue_labels.description, issue_author_login, issue_author_type, issue_author_association, issue_assignee_id, issue_assignee_login, issue_assignees.id, issue_assignees.login, issue_created_at, issue_updated_at, issue_closed_at, issue_comments}；此外需要从GitHub REST API获取的额外属性{html_url, state, locked, reactions, timeline_url, performed_via_github_app}，API示例https://api.github.com/repos/rails/rails/issues/52770
      - D = {_issue_exid(PK) string, issue_id int, repo_id int, issue_number int, issue_author_id int, issue_title string, body string}
      - F = {_issue_exid: (join, [repo_id, '#', issue_number]), issue_title: lambda _issue_exid: _get_field_from_db('issue_title', {'type': 'IssuesEvent', 'repo_id': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['repo_id'], 'issue_number': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['issue_number']}), body: lambda _issue_exid: _get_field_from_db('body', {'type': 'IssuesEvent', 'repo_id': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['repo_id'], 'issue_number': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['issue_number']})}
    - E: Repo
      - U_K = {rep_id(PK), _repo_full_name, repo_name, _owner_id, _name, org_id}
      - U_V = {repo_description}  # _repo_full_name在快照时刻具有唯一性，同样可作为快照key。clickhouse可查属性{org_login, repo_size, repo_created_at, repo_updated_at, repo_pushed_at, repo_stargazers_count, repo_forks_count, repo_language, repo_has_issues, repo_has_projects, repo_has_downloads, repo_has_wiki, repo_has_pages, repo_license, repo_default_branch, _repo_default_branch_exid, repo_topics.name}  # repo_created_at是clickhouse数据库中的字段，对应于REST API的字段名created_at，为了容易区分不同字段的属性，采用clickhouse字段命名风格，在相同属性名前加上实体名前缀并以下划线连接；采用_repo_full_name表示"X-lab2017/open-digger"，与GitHub REST API保持一定的一致性，如repo下的name与full_name的区分: https://api.github.com/repos/X-lab2017/open-digger； 此外需要从GitHub REST API获取的额外属性{__repo_is_fork, __repo_parent_id, html_url, forks_url, branches_url, tags_url, languages_url, stargazers_url, contributors_url, subscribers_url, commits_url, contents_url, issues_url, pulls_url, releases_url, git_url, ssh_url, clone_url, svn_url, homepage, watchers_count, archived, open_issues_count, network_count, subscribers_count}。
      - D = {rep_id(PK) int, _repo_full_name string, repo_name string, _owner_id int, _name string(255), org_id int, repo_description string}
      - F = {_repo_full_name: repo_name, _owner_id: (if, actor_login==repo_name.split('/')[0]?actor_id:get_actor_id_by_actor_login(repo_name.split('/')[0])), _name: repo_name.split('/')[1], repo_description: lambda repo_id: _get_field_from_db('repo_description', {'type': 'PullRequestEvent', 'repo_id': repo_id})}   # 其他重要属性{_repo_default_branch_exid: (join, [repo_id, ':', repo_default_branch]), __repo_parent_id: (if, __repo_is_fork?__repo.parent.id:None)}
  - 识别结果：
    - 实体对象类型： {Actor: [actor1, actor2], Repo: [repo1], Issue: [issue1, issue2]}
    - 实体对象属性： {actor1: Actor{'actor_id': 115639837}, actor2: Actor{'actor_id': 37795442}, repo1: Repo{'repo_id': 288431943}, issue1: Issue{'_issue_exid': '288431943#1238'}, issue2: Issue{'_issue_exid': '288431943#1237'}}
    
  
- 关系抽取：
  - 关系模式Relation Schema: R(U, D, DOM, F)，其中R为关系名，U为组成该关系的属性名集合，D为属性组U中属性所来自的域，DOM为属性向域的映象集合，F为属性间数据的依赖关系集合。
    - R = {EventAction, Reference}
    - U = {source, type, target}
    - D = {Actor, Repo, Issue}
    - DOM = D + {External_Links}
    - F = None
  - tuples = [
    - (issue1{"src_entity_id": "288431943#1238", "src_entity_type": "Issue"}, actor1{"tar_entity_id": "115639837", "tar_entity_type": "Actor"}, relation{"relation_label_id":"0", "relation_type": "EventAction", "relation_label_repr": "Issue_OpenedBy_Actor"}, event{"event_id": "27901170588", "event_trigger": "IssuesEvent::action=opened", "event_type": "IssuesEvent", "event_time": "2023-03-22 14:03:48"}, ner{"tar_entity_match_text": "", "tar_entity_match_pattern_type": "", "tar_entity_objnt_prop_dict": ""}),
    - (issue1, relation{"relation_label_id":"1", "relation_type": "EventAction", "relation_label_repr": "Issue_CreatedIn_Repo"}, repo1, event, ner),
    - (issue1, relation{"relation_label_id":"2", "relation_type": "Reference", "relation_label_repr": "Issue_unknown_UnknownFromBodyRef"}, actor2, event, ner),
    - (issue1, relation{"relation_label_id":"2", "relation_type": "Reference", "relation_label_repr": "Issue_unknown_UnknownFromBodyRef"}, issue2, event, ner),
    - ~~(actor1, relation, repo1, event, ner),  # 复合关系~~
    - ~~(actor1, relation, actor2, event, ner)  # 复合关系~~
    - ~~(actor1, relation, issue2, event, ner)  # 复合关系~~
  - ]
  
- 事件抽取[1,5]：（暂时不做事理图谱）

    - 事件触发词trigger: [IssuesEvent::action=opened]; 
    
    - 事件论元argument: {"subject": "actor1", "object": "issue1", "time": "2023-03-22 14:03:48", "location": "repo1", "object_referenced_by_body": ["actor2", "issue2"]};
    
    - 事件属性Attribute: {"event_type": "IssuesEvent", "action": "opened", "polairty": 0} # polairty与emoji和文本情感倾向有关，其中互动类型的事件与emoji有关。
    
## 2.3 参考资料

- [1] [A Survey on Deep Learning Event Extraction: Approaches and Applications](https://arxiv.org/pdf/2107.02126.pdf), 
- [2] [Event Extraction.pdf](http://ir.hit.edu.cn/~xiachongfeng/slides/Event%20Extraction.pdf),
- [3] [SENTiVENT: enabling supervised information extraction of company-specific events in economic and financial news](https://link.springer.com/content/pdf/10.1007%2Fs10579-021-09562-4.pdf).
- [4] [Information as thing](https://onlinelibrary.wiley.com/doi/abs/10.1002/%28SICI%291097-4571%28199106%2942%3A5%3C351%3A%3AAID-ASI5%3E3.0.CO%3B2-3)
- [5] [Classification, Links, and Contexts: Making Sense and Using Logic.](https://people.ischool.berkeley.edu/~buckland/lisbon15.pdf)
- [6] [The concept of information](https://onlinelibrary.wiley.com/doi/abs/10.1002/aris.1440370109)

## 2.4 GitHub日志信息抽取

### 2.4.1 实体识别
  - 概念模型的实体类型集
  ```
  EC = 
    {
      'Actor',
      'Branch',
      'Commit',
      'CommitComment',
      'Gollum',
      'Issue',
      'IssueComment',
      # 'IssuesReaction',
      # 'Public',
      'PullRequest',
      'PullRequestReview',
      'PullRequestReviewComment',
      'Push',
      'Release',
      'Repo',
      'Tag'
    }
  ```
  
  - 每个实体类型的关键码
  ```
  EC_PK = {
    'Actor': 'actor_id',  # 识别文本示例：@{actor_login} or /{actor_login}
    'Branch': '_branch_exid',  # 需要用它连接PullRequest与commit，识别文本示例：/{_repo_full_name}/tree/{branch_name}
    'Commit': 'commit_sha',  # 识别文本示例：/{_repo_full_name}/commit/{commit_sha} or /{_repo_full_name}/pull/{issue_number}/commits/{commit_sha}，验证存在后的{commit_sha} or {commit_sha[:7]}
    'CommitComment': 'commit_comment_id',  # 识别文本示例：/{_repo_full_name}/commit/{commit_sha}#commitcomment-{commit_comment_id}
    'Gollum': '_gollum_exid',  # 识别文本示例：/{_repo_full_name}/wiki
    'Issue': '_issue_exid',  # 为了与拥有多个issue_id的PullRequest统一，使用{repo_id}#{issue_number}模式作为主键，
    #  # 识别文本示例：/{_repo_full_name}/issues/{issue_number} or /{_repo_full_name}/issues/{issue_number}#issue-{issue_id} or 
    #  # /{_repo_full_name}#{issue_number} or #{issue_number} or [Ii]ssue#{issue_number}
    'IssueComment': 'issue_comment_id',  # 识别文本示例：/{_repo_full_name}/(?:issues|pull)/{issue_number}#issuecomment-{issue_comment_id}
    # 'IssuesReaction': None,  # 识别文本示例: 无
    # 'Public': None,  # 识别文本示例: 无
    'PullRequest': '_issue_exid',  # 识别文本示例：Issue的所有识别方式 or /{_repo_full_name}/pull/{issue_number} or /{_repo_full_name}/pull/{issue_number}#issue-{issue_id}
    'PullRequestReview': 'pull_review_id',  # 识别文本示例：/{_repo_full_name}/(?:issues|pull)/{issue_number}#pullrequestreview-{pull_review_id}
    'PullRequestReviewComment': 'pull_review_comment_id',  # 识别文本示例：/{_repo_full_name}/(?:issues|pull)/{issue_number}/files#r{pull_review_comment_id} 
    #  # or /{_repo_full_name}/(?:issues|pull)/{issue_number}/files/{push_head}#r{pull_review_comment_id} or 
    #  # /{_repo_full_name}/(?:issues|pull)/{issue_number}#discussion_r{pull_review_comment_id}
    'Push': 'push_id',  # 需要用它连接PullRequest与commit，识别文本示例: 无
    'Release': 'release_id',  # 识别文本示例: /{_repo_full_name}/releases/tag/{release_tag_name}
    'Repo': 'repo_id',  # 识别文本示例: /{_repo_full_name}
    'Tag': '_tag_exid',  # 需要用它连接release与commit，识别文本示例: 与Branch相同/{_repo_full_name}/tree/{tag_name}
  }
  ```
  
  - 实体型Entity Type：E(U, D, F)，其中E为实体名，U为组成该实体概念的属性名集合，D为属性组U中属性所来自的域，F为属性间数据的依赖关系集合。
    - E: Actor
      - U_K = {actor_id(PK), actor_login}  # PK表示关键码，以_开头表示需要在clickhouse数据库已有属性的基础上进一步处理，以__开头表示需要使用GitHub REST API或GitHub GraphQL API。actor_login在快照时刻具有唯一性，同样可作为快照key。
      - U_V = None  # clickhouse中可查属性{issue_author_type, issue_comment_author_type, pull_merged_by_type, pull_requested_reviewer_type, pull_review_comment_author_type, fork_forkee_owner_type, delete_pusher_type, create_pusher_type, member_type, release_author_type, commit_comment_author_type}；此外需要从GitHub REST API获取的额外属性{type, html_url, followers_url, following_url, gists_url, starred_url, subscriptions_url, organizations_url, repos_url, events_url, received_events_url, name, company, blog, email, public_repos, public_gists, followers, following}, 其中除delete_pusher_type与create_pusher_type外，其他actor type取值类型ActorType = Enum8('Bot' = 1, 'Mannequin' = 2, 'Organization' = 3, 'User' = 4), API示例https://api.github.com/users/ClickHouse 或 https://api.github.com/user/54801242
      - D = {actor_id(PK) int, actor_login string(39)}
      - F = None
      
    - E: Branch
      - U_K = {_branch_exid(PK), repo_id, branch_name}  # branch_name需要按事件解析并作为实参输入
      - U_V = None  # clickhouse中可查属性{repo_name}；此外需要从GitHub REST API获取的额外属性{html_url, commit_sha, protected}, 示例：https://api.github.com/repos/rails/rails/branches/2-2-stable
      - D = {_branch_exid(PK) string, repo_id int, branch_name string}
      - F = {_branch_exid: (join, [repo_id, ':', branch_name])}  # branch_name: (case, [PullRequestEvent::action=opened, PullRequestEvent::action=closed&pull_merged=True, PullRequestReviewEvent::action=created, PushEvent::action=added, CreateEvent::action=added&create_ref_type=branch, CreateEvent::action=added&create_ref_type=tag, DeleteEvent::action=added&create_ref_type=branch], [[pull_head_ref, pull_base_ref], [pull_head_ref, pull_base_ref], pull_head_ref, _trim_refs_heads(push_ref), [create_ref, create_master_branch], create_master_branch, delete_ref])
      
    - E: Commit
      - U_K = {commit_sha(PK), repo_id, _commit_author_id, __commit_parents_sha}
      - U_V = {_push_commits_message}  # clickhouse中的push_commits.message中含有的.被转为_，clickhouse其他可查属性{repo_name, created_at, push_commits.name, push_commits.email}；此外需要从GitHub REST API获取的额外属性{html_url, comments_url, committer, stats, files}，其中重要属性files暂不考虑加入网络
      - D = {commit_sha(PK) string, repo_id int, _commit_author_id int, __commit_parents_sha list[string], _push_commits_message string}  # __commit_parents_sha示例：getJson(https://api.github.com/repos/tidyverse/ggplot2/commits/8041c84bf958285fa16301204ac464422373e589).parents.[i].sha
      - F = {_commit_author_id: lambda commit_sha: _get_field_from_db('actor_id', {'type': 'PushEvent', 'push_head': commit_sha}), __commit_parents_sha: __get_commit_parents_sha(commit_sha, repo_id), _push_commits_message: lambda commit_sha: _get_field_from_db('push_commits.message', {'type': 'PushEvent', 'push_head': commit_sha})}
      
    - E: CommitComment
      - U_K = {commit_comment_id(PK), commit_comment_author_id, commit_comment_sha}
      - U_V = {body}  # clickhouse可查属性{created_at, commit_comment_author_login, commit_comment_author_type, commit_comment_author_association, commit_comment_path, commit_comment_position, commit_comment_line, commit_comment_created_at, commit_comment_updated_at}; 此外需要从GitHub REST API获取的额外属性{html_url, reactions}, API示例https://api.github.com/repos/rails/rails/comments/9531809
      - D = {commit_comment_id(PK) int, commit_comment_author_id int, commit_comment_sha string, body string}
      - F = {body: lambda commit_comment_id: _get_field_from_db('body', {'type': 'CommitCommentEvent', 'commit_comment_id': commit_comment_id})}
      
    - E: Gollum
      - U_K = {_gollum_exid(PK), repo_id}
      - U_V = None  # clickhouse可查属性{repo_name, created_at, repo_has_wiki, gollum_pages.page_name, gollum_pages.title, gollum_pages.action}，其中repo_has_wiki仅在PullRequestEvent,PullRequestReviewEvent,PullRequestReviewCommentEvent时显示正确。
      - D = {_gollum_exid(PK) int, repo_id int}
      - F = {_gollum_exid: (join, [repo_id, ':', "wiki"])}
      
    - E: Issue
      - U_K = {_issue_exid(PK), issue_id, repo_id, issue_number, issue_author_id}
      - U_V = {issue_title, body}  # issue_title, body需去重（action = closed reopened labeled冗余，可只取opened），clickhouse可查属性{actor_id, actor_login, repo_name, org_id, org_login, created_at, issue_labels.name, issue_labels.default, issue_labels.description, issue_author_login, issue_author_type, issue_author_association, issue_assignee_id, issue_assignee_login, issue_assignees.id, issue_assignees.login, issue_created_at, issue_updated_at, issue_closed_at, issue_comments}；此外需要从GitHub REST API获取的额外属性{html_url, state, locked, reactions, timeline_url, performed_via_github_app}，API示例https://api.github.com/repos/rails/rails/issues/52770
      - D = {_issue_exid(PK) string, issue_id int, repo_id int, issue_number int, issue_author_id int, issue_title string, body string}
      - F = {_issue_exid: (join, [repo_id, '#', issue_number]), issue_title: lambda _issue_exid: _get_field_from_db('issue_title', {'type': 'IssuesEvent', 'repo_id': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['repo_id'], 'issue_number': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['issue_number']}), body: lambda _issue_exid: _get_field_from_db('body', {'type': 'IssuesEvent', 'repo_id': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['repo_id'], 'issue_number': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['issue_number']})}
      
    - E: IssueComment
      - U_K = {issue_comment_id(PK), _issue_exid, repo_id, issue_number, issue_comment_author_id}
      - U_V = {body}  # clickhouse可查属性{issue_id, repo_name, created_at, issue_comment_created_at, issue_comment_updated_at, issue_comment_author_association, issue_comment_author_login, issue_comment_author_type}; 此外需要从GitHub REST API获取的额外属性{html_url, reactions}, API示例https://api.github.com/repos/rails/rails/issues/comments/2325077114  # 由于IssueComment和IssuesReaction可以是对Issue和PullRequest的动作，因此Issue和PullRequest的id字段统一使用_issue_exid。
      - D = {issue_comment_id(PK) int, _issue_exid string, repo_id int, issue_number int, issue_comment_author_id int, body string}
      - F = {_issue_exid: (join, [repo_id, '#', issue_number]), body: lambda issue_comment_id: _get_field_from_db('body', {'type': 'IssueCommentEvent', 'issue_comment_id': issue_comment_id})}
      
    - E: PullRequest
      - U_K = {_issue_exid(PK), issue_id, repo_id, issue_number, issue_author_id, pull_merge_commit_sha, pull_merged_by_id, _pull_base_branch_exid, pull_base_ref, _pull_head_branch_exid, pull_head_repo_id, pull_head_ref}
      - U_V = {issue_title, body}  # issue_title, body需去重（action = closed reopened labeled冗余，可只取opened），clickhouse可查属性{actor_id, actor_login, repo_name, org_id, org_login, created_at, issue_labels.name, issue_labels.default, issue_labels.description, issue_author_login, issue_author_type, issue_author_association, issue_assignee_id, issue_assignee_login, issue_assignees.id, issue_assignees.login, issue_created_at, issue_updated_at, issue_closed_at, issue_comments, pull_commits, pull_additions, pull_deletions, pull_changed_files, pull_merged, pull_merged_at, pull_merged_by_login, pull_merged_by_type, pull_head_repo_name}；此外需要从GitHub REST API获取的额外属性{html_url, state, locked, reactions, timeline_url, performed_via_github_app}, 其中相同issue_number使用issues和pulls两种访问方式时有着不同的issue_id，分别为IC和PRRC的根节点。IC API示例https://api.github.com/repos/rails/rails/issues/52770/comments ，PRRC对应的API示例https://api.github.com/repos/rails/rails/pulls/52770/comments
      - D = {_issue_exid(PK) string, issue_id int, repo_id int, issue_number int, issue_author_id int, pull_merge_commit_sha string, pull_merged_by_id int, _pull_base_branch_exid string, pull_base_ref string, _pull_head_branch_exid string, pull_head_repo_id int, pull_head_ref string, issue_title str, body str}
      - F = {_issue_exid: (join, [repo_id, '#', issue_number]), _pull_base_branch_exid: (join, [repo_id, ':', pull_base_ref]), _pull_head_branch_exid: (join, [pull_head_repo_id, ':', pull_head_ref]), issue_title: lambda _issue_exid: _get_field_from_db('issue_title', {'type': 'PullRequestEvent', 'repo_id': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['repo_id'], 'issue_number': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['issue_number']}), body: lambda _issue_exid: _get_field_from_db('body', {'type': 'PullRequestEvent', 'repo_id': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['repo_id'], 'issue_number': Obj_exid.get_kwargs_from_exid('_issue_exid', _issue_exid)['issue_number']})}
      
    - E: PullRequestReview
      - U_K = {pull_review_id(PK), _issue_exid, repo_id, issue_id, issue_number, pull_requested_reviewer_id, _pull_head_branch_exid, pull_head_repo_id, pull_head_ref}
      - U_V = {body}  # clickhouse可查属性{repo_name, created_at, pull_merge_commit_sha, pull_requested_reviewer_login, pull_requested_reviewer_type, pull_review_comments, pull_review_state, pull_review_author_association}; 此外需要从GitHub REST API获取的额外属性{html_url}, API示例https://api.github.com/repos/rails/rails/pulls/52770/reviews/2275794464
      - D = {pull_review_id(PK) int, _issue_exid string, repo_id int, issue_id int, issue_number int, pull_requested_reviewer_id int, _pull_head_branch_exid string, pull_head_repo_id int, pull_head_ref string, body string}
      - F = {_issue_exid: (join, [repo_id, '#', issue_number]), _pull_head_branch_exid: (join, [pull_head_repo_id, ':', pull_head_ref]), body: lambda pull_review_id: _get_field_from_db('body', {'type': 'PullRequestReviewEvent', 'pull_review_id': pull_review_id})}
      
    - E: PullRequestReviewComment
      - U_K = {pull_review_comment_id(PK), _issue_exid, repo_id, issue_id, issue_number, pull_review_id, pull_review_comment_author_id, push_head}
      - U_V = {body}  # clickhouse可查属性{repo_name, created_at, issue_title, body, pull_review_comment_path, pull_review_comment_position, pull_review_comment_author_login, pull_review_comment_author_type, pull_review_comment_author_association, pull_review_comment_created_at, pull_review_comment_updated_at}; 此外需要从GitHub REST API获取的额外属性{html_url, reactions, line, original_line, in_reply_to_id, position, original_position}，PRRC API示例https://api.github.com/repos/rails/rails/pulls/comments/1741029930 而IC API示例https://api.github.com/repos/rails/rails/issues/comments/169
      - D = {pull_review_comment_id(PK) int, _issue_exid string, repo_id int, issue_id int, issue_number int, pull_review_id int, pull_review_comment_author_id int, push_head string, body string}
      - F = {_issue_exid: (join, [repo_id, '#', issue_number]), body: lambda pull_review_comment_id: _get_field_from_db('body', {'type': 'PullRequestReviewCommentEvent', 'pull_review_comment_id': pull_review_comment_id})}
      
    - E: Push
      - U_K = {push_id(PK), actor_id, _push_branch_exid, repo_id, push_ref, push_head}
      - U_V = None   # clickhouse可查属性{actor_login, repo_name, created_at, push_size, push_distinct_size, push_commits.name, push_commits.email, push_commits.message}  # 可通过name和email字段获取login和id 见https://www.coder.work/article/3180620
      - D = {push_id(PK) int, actor_id int, _push_branch_exid string, repo_id int, push_ref string, push_head string}
      - F = {_push_branch_exid: (join, [repo_id, ':', _trim_refs_heads(push_ref)])}
      
    - E: Release
      - U_K = {release_id(PK), release_author_id, _release_tag_exid, repo_id, release_tag_name, release_name}
      - U_V = {release_body}  # clickhouse可查属性{repo_name, created_at, release_target_commitish, release_draft, release_author_login, release_author_type, release_prerelease, release_created_at, release_published_at, release_assets.name, release_assets.uploader_login, release_assets.uploader_id, release_assets.content_type, release_assets.state, release_assets.size, release_assets.download_count}，此外需要从GitHub REST API获取的额外属性{html_url, assets_url, reactions}，API示例https://api.github.com/repos/rails/rails/releases/171548858
      - D = {release_id(PK) int, release_author_id int, _release_tag_exid string, repo_id int, release_tag_name string, release_name string, release_body string}
      - F = {_release_tag_exid: (join, [repo_id, '@', release_tag_name]), release_body: lambda release_id: _get_field_from_db('release_body', {'type': 'ReleaseEvent', 'release_id': release_id})}
      
    - E: Repo
      - U_K = {rep_id(PK), _repo_full_name, repo_name, _owner_id, _name, org_id}
      - U_V = {repo_description}  # _repo_full_name在快照时刻具有唯一性，同样可作为快照key。clickhouse可查属性{org_login, repo_size, repo_created_at, repo_updated_at, repo_pushed_at, repo_stargazers_count, repo_forks_count, repo_language, repo_has_issues, repo_has_projects, repo_has_downloads, repo_has_wiki, repo_has_pages, repo_license, repo_default_branch, _repo_default_branch_exid, repo_topics.name}  # repo_created_at是clickhouse数据库中的字段，对应于REST API的字段名created_at，为了容易区分不同字段的属性，采用clickhouse字段命名风格，在相同属性名前加上实体名前缀并以下划线连接；采用_repo_full_name表示"X-lab2017/open-digger"，与GitHub REST API保持一定的一致性，如repo下的name与full_name的区分: https://api.github.com/repos/X-lab2017/open-digger； 此外需要从GitHub REST API获取的额外属性{__repo_is_fork, __repo_parent_id, html_url, forks_url, branches_url, tags_url, languages_url, stargazers_url, contributors_url, subscribers_url, commits_url, contents_url, issues_url, pulls_url, releases_url, git_url, ssh_url, clone_url, svn_url, homepage, watchers_count, archived, open_issues_count, network_count, subscribers_count}。
      - D = {rep_id(PK) int, _repo_full_name string, repo_name string, _owner_id int, _name string(255), org_id int, repo_description string}
      - F = {_repo_full_name: repo_name, _owner_id: (if, actor_login==repo_name.split('/')[0]?actor_id:get_actor_id_by_actor_login(repo_name.split('/')[0])), _name: repo_name.split('/')[1], repo_description: lambda repo_id: _get_field_from_db('repo_description', {'type': 'PullRequestEvent', 'repo_id': repo_id})}   # 其他重要属性{_repo_default_branch_exid: (join, [repo_id, ':', repo_default_branch]), __repo_parent_id: (if, __repo_is_fork?__repo.parent.id:None)}
      
    - E: Tag  # type: CreateEvent, DeleteEvent, ReleaseEvent
      - U_K = {_tag_exid(PK), repo_id, tag_name, _tag_branch_exid, tag_branch_name}  # tag_name, tag_branch_name需解析并输入
      - U_V = None  # clickhouse可查属性{type, create_ref, delete_ref, release_tag_name, create_master_branch, release_target_commitish, delete_ref_type, delete_pusher_type, create_ref_type, create_pusher_type, create_description}; 此外需要从GitHub REST API获取的额外属性{zipball_url, tarball_url}，API示例https://api.github.com/repos/X-lab2017/open-digger/tags  # create_description仅在CreateEvent::create_ref_type='tag'时取值
      - D = {_tag_exid(PK) string, repo_id int, tag_name string, _tag_branch_exid string, tag_branch_name string}
      - F = {_tag_exid: (join, [repo_id, '@', tag_name]), _tag_branch_exid: lambda repo_id, tag_branch_name: Obj_exid.get_exid('_tag_branch_exid', {"repo_id": repo_id, "branch_name": tag_branch_name})} # 注意：tag_name, tag_branch_name在不同的事件中需要分别解析，tag_name: case(type, [CreateEvent, DeleteEvent, ReleaseEvent], [create_ref, delete_ref, release_tag_name]), tag_branch_name: case(type, [CreateEvent, DeleteEvent, ReleaseEvent], [create_master_branch, None, release_target_commitish]).

### 2.4.2 关系抽取

详见[ER_config.py](../GH_CoRE/model/ER_config.py).

### 2.4.3 事件抽取

暂时忽略。

## 2.5 reference relation csv headline design

head: [src_entity_id, src_entity_type, tar_entity_id, tar_entity_type, relation_label_id, relation_type, relation_label_repr, event_id, event_trigger, event_type, event_time, tar_entity_match_text, tar_entity_match_pattern_type, tar_entity_objnt_prop_dict]. 
其中relation_type指Reference或EventAction。
任务相近的项目：https://github.com/empiricalstateofmind/eventgraphs/blob/master/examples/eventgraphs_tutorial.ipynb
