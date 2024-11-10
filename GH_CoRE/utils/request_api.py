#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/10/23 2:01
# @Author : 'Lou Zehua'
# @File   : request_api.py 

import random
import requests
import time


GITHUB_TOKENS = ['GITHUB_TOKEN_1', 'GITHUB_TOKEN_2']


class RequestAPI:
    base_url = ''
    token = ''
    headers = {
        "Authorization": f"token {token}"
    }
    username = ''
    password = ''
    query = None  # for post json
    default_method = 'GET'

    def __init__(self, auth_type='token', token=None, headers=None, username=None, password=None, query=None,
                 method=None, **kwargs):
        self.auth_type = auth_type  # 'token', 'password'
        self.base_url = self.__class__.base_url
        self.query = query or self.__class__.query
        self.method = method or self.__class__.default_method
        if self.auth_type == 'token':
            self.token = token or self.__class__.token
            self.headers = headers or self.__class__.headers
        elif self.auth_type == 'password':
            self.username = username or self.__class__.username
            self.password = password or self.__class__.password
            self.auth = (self.username, self.password)
        else:
            raise ValueError("auth_type must be in ['token', 'password'].")
        self.__dict__.update(**kwargs)

    def update_headers(self):
        self.headers['Authorization'] = f"token {self.token}"
        return None

    def request_get(self, url=None):
        url = url or self.base_url
        if self.auth_type == 'token':
            response = requests.get(url, headers=self.headers)
        elif self.auth_type == 'password':
            response = requests.get(url, auth=self.auth)
        else:
            raise ValueError("auth_type must be in ['token', 'password'].")
        return response

    def request_post(self, query, base_url=None, **kwargs):
        self.base_url = base_url or self.base_url
        self.query = query or self.query
        variables = kwargs.pop("variables") if "variables" in kwargs.keys() else None
        if self.auth_type == 'token':
            # print(base_url, self.query, self.headers)
            response = requests.post(self.base_url, json={'query': self.query, "variables": variables}, headers=self.headers, **kwargs)
        elif self.auth_type == 'password':
            response = requests.post(self.base_url, json={'query': self.query, "variables": variables}, auth=self.auth, **kwargs)
        else:
            raise ValueError("auth_type must be in ['token', 'password'].")
        return response

    def request(self, url, method=None, retry=1, default_break=60, query=None, **kwargs):
        self.method = method or self.method
        self.method = self.method.upper()
        while retry >= 0:
            try:
                if self.method == 'GET':
                    response = self.request_get(url)
                elif self.method == 'POST':
                    response = self.request_post(base_url=url, query=query, **kwargs)
                else:
                    raise ValueError(f"The {method} should be in ['GET', 'POST']!")
            except requests.exceptions.ProxyError as e:
                print(f"Crawling speed is too fast, take a break {default_break} sec.")
                time.sleep(default_break)
            except requests.exceptions.SSLError as e:
                print(f"Crawling speed is too fast, take a break {default_break} sec.")
                time.sleep(default_break)
            except requests.exceptions.ConnectionError as e:
                print(f"Crawling speed is too fast, take a break {default_break} sec.")
                time.sleep(default_break)
            else:
                if response.status_code == 200:
                    return response
                else:
                    print(f"Error fetching {url}: {response.status_code}.")
                    return None
            time.sleep(random.randint(1, 3))
            retry -= 1
        return None


class GitHubTokenPool:

    def __init__(self, github_tokens=None):
        self.github_tokens = github_tokens
        if self.github_tokens is None:
            try:
                from etc.authConf import GITHUB_TOKENS as LOC_GITHUB_TOKENS
                self.github_tokens = LOC_GITHUB_TOKENS
            except:
                self.github_tokens = GITHUB_TOKENS
        self.tokenState_list = self.init_tokenState_list()
        self.minTime_tokenState = {"token": '', "remaining": 0, "reset": float(time.time())}

    def init_tokenState_list(self):
        return [{"token": token, "remaining": 1, "reset": float(time.time())} for token in self.github_tokens]

    def get_GithubToken(self):
        if not self.tokenState_list:
            self.tokenState_list = self.init_tokenState_list()

        for tokenState in self.tokenState_list:
            if tokenState['remaining'] > 0:
                return tokenState['token']
            if self.minTime_tokenState['reset'] > tokenState['reset']:
                self.minTime_tokenState = tokenState

        sleep_time = int(self.minTime_tokenState['reset'] - time.time())
        if sleep_time > 0:
            print(f'Sleep {str(sleep_time)} sec')
            time.sleep(sleep_time)

        return self.minTime_tokenState['token']

    def update_GithubTokenState_list(self, token, response):
        if not response:
            return None
        for i, tokenState in enumerate(self.tokenState_list):
            if token == tokenState['token']:
                if response.status_code in [429, 401, 403]:
                    tokenState['remaining'] = 0
                if 'X-RateLimit-Remaining' in response.headers:
                    tokenState['remaining'] = int(response.headers['X-RateLimit-Remaining'])

                if 'X-RateLimit-Reset' in response.headers:
                    tokenState['reset'] = int(response.headers['X-RateLimit-Reset'])
                elif 'Retry-After' in response.headers:
                    tokenState['reset'] = int(time.time()) + int(response.headers['Retry-After']) + 1

                self.tokenState_list[i] = tokenState
        return None


class RequestGitHubAPI(RequestAPI):
    base_url = 'https://api.github.com/'
    token_pool = GitHubTokenPool()
    token = token_pool.github_tokens[0] if token_pool.github_tokens else ''
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.4; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2225.0 Safari/537.36'
    }
    default_method = 'GET'
    url_pat_mode = 'name'

    def __init__(self, url_pat_mode=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__.update(**kwargs)
        self.token_pool = kwargs.get("token_pool", None) or self.__class__.token_pool
        self.url_pat_mode = url_pat_mode or self.__class__.url_pat_mode
        if self.url_pat_mode == 'id':
            self.user_url_pat = self.__class__.base_url + 'user/{actor_id}'  # https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28#get-a-user-using-their-id
            self.repo_url_pat = self.__class__.base_url + 'repositories/{repo_id}'  # https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-public-repositories
        elif self.url_pat_mode == 'name':
            self.user_url_pat = self.__class__.base_url + 'users/{actor_login}'  # https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28#get-a-user
            self.repo_url_pat = self.__class__.base_url + 'repos/{owner}/{repo}'  # https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#get-a-repository
        else:
            raise ValueError("url_pat_mode must be in ['id', 'name'].")
        self.commit_url_pat = self.repo_url_pat + '/commits/{commit_sha}'
        self.blob_url_pat = self.repo_url_pat + '/git/blobs/{sha}'

    def get_url(self, url_type="repo_ext", ext_pat=None, params=None):
        url = None
        params = params or {}
        if url_type.startswith("actor") or url_type.startswith("user"):
            url = self.user_url_pat.format(**params)
        elif url_type.startswith("repo"):
            url = self.repo_url_pat.format(**params)
        elif url_type.startswith("commit"):
            url = self.commit_url_pat.format(**params)
        else:
            return None
        if url_type.endswith("ext") and ext_pat:
            url += ext_pat.format(**params)
        return url

    def request(self, url, method=None, retry=1, default_break=60, query=None, **kwargs):
        url = url or self.base_url
        self.token = self.token_pool.get_GithubToken()
        self.update_headers()
        response = RequestAPI.request(self, url=url, method=method, retry=retry, default_break=default_break,
                                      query=query, **kwargs)
        self.token_pool.update_GithubTokenState_list(self.token, response)
        return response


class GitHubGraphQLAPI(RequestAPI):
    base_url = 'https://api.github.com/graphql'
    token_pool = GitHubTokenPool()
    token = token_pool.github_tokens[0] if token_pool.github_tokens else ''
    headers = {
        'Authorization': 'bearer ' + token,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.4; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2225.0 Safari/537.36'
    }
    default_method = 'POST'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__.update(**kwargs)
        self.token_pool = kwargs.get("token_pool", None) or self.__class__.token_pool

    def request(self, query, url=None, method=None, retry=1, default_break=60, **kwargs):
        url = url or self.base_url
        self.token = self.token_pool.get_GithubToken()
        self.update_headers()
        response = RequestAPI.request(self, query=query, url=url, method=method, retry=retry,
                                      default_break=default_break, **kwargs)
        self.token_pool.update_GithubTokenState_list(self.token, response)
        return response


if __name__ == '__main__':
    repo_name = "redis/redis"
    query_tags = """
    {
      repository(owner: "%s", name: "%s") {
        refs(refPrefix: "refs/tags/", first: 100) {
          edges {
            node {
              name
              target {
                ... on Tag {
                  tagger {
                    date
                  }
                  message
                }
              }
            }
          }
        }
      }
    }
    """ % (repo_name.split('/')[0], repo_name.split('/')[1])
    query_graphql_api = GitHubGraphQLAPI()
    print(query_graphql_api.token_pool.tokenState_list)
    response = query_graphql_api.request(query_tags)
    data = response.json()
    print(bool(data))
    print(query_graphql_api.token_pool.tokenState_list)
    response = query_graphql_api.request(query_tags)
    data = response.json()
    print(bool(data))
    print(query_graphql_api.token_pool.tokenState_list)
