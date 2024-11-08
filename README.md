# GitHub_Collaboration_Relation_Extraction
Collaboration Relation Extraction from GitHub logs. Collaboration relations include 2 categories: `EventAction` relations and `Reference` relations. This is a relation extraction tool for Project https://github.com/birdflyi/OSDB_STN_reference_coupling_data_analysis.

# Quick Start
1. Download the directory `etc/` and file `main.py` in [GitHub_Collaboration_Relation_Extraction](https://github.com/birdflyi/GitHub_Collaboration_Relation_Extraction.git) into the root directory of your new project.
2. Change the default settings in `etc/authConf.py`.

- AuthConfig
  - You need to set the DEFAULT_INTMED_MODE in [I_AUTH_SETTINGS_LOCAL_HOSTS, I_AUTH_SETTINGS_ALIYUN_HOSTS, I_AUTH_SETTINGS_ALIYUN_INTERMEDIATE_HOSTS], and set the corresponding auth_settings_xxx_hosts dict.
  - If you have an Aliyun Cloud or other database service within github log tables, please set the server authorization information below the line [Aliyun](https://github.com/birdflyi/GitHub_Collaboration_Relation_Extraction/blob/4c5d0fb0a90ad563ff20d98a02338f09d17257b0/etc/authConf.py#L30)
  - If you want a sample dataset to start, you can Download a [ClickHouse sample data](https://github.com/X-lab2017/open-digger/blob/master/sample_data/README.md#current-sample-datasets) for your docker container, and set the server authorization information below the line [local docker image](https://github.com/birdflyi/GitHub_Collaboration_Relation_Extraction/blob/4c5d0fb0a90ad563ff20d98a02338f09d17257b0/etc/authConf.py#L17).
- GITHUB_TOKENS
  - You need to replace the GITHUB_TOKENS with effective GitHub tokens start with 'gh', if you donot have any GitHub token, try to [Creating a fine-grained personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token).

3. Change the settings in `main.py` and run it.
- Change the `repo_names` and `year` settings
  - Notes: It may take a lot of time to process all records. Set `limit` as a positive integer to limit the max number of records when you just want to take a test.
- Create the `data/` directory
  - Create the directory in the root directory of your project: data_dirs = ['data', 'data/github_osdb_data', 'data/global_data', 'data/github_osdb_data/repos', 'data/github_osdb_data/repos_dedup_content', 'data/github_osdb_data/GitHub_Collaboration_Network_repos']. Make directories:

```python
import os

base_dir = '' or os.getcwd()  # you can set a base dir or use the current dir by default.
data_dirs = ['data', 'data/github_osdb_data', 'data/global_data', 'data/github_osdb_data/repos', 'data/github_osdb_data/repos_dedup_content', 'data/github_osdb_data/GitHub_Collaboration_Network_repos']
for rel_data_dir in data_dirs:  \
    os.makedirs(os.path.join(base_dir, rel_data_dir), exist_ok=True)  # avoid the FileExistsError
```
