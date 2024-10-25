#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/10/23 2:01
# @Author : 'Lou Zehua'
# @File   : request_api.py 

import random
import requests
import time


GITHUB_TOKEN = 'YOUR_GITHUB_TOKEN'


class RequestAPI:
    base_url = ''
    token = ''
    headers = {
        "Authorization": f"token {token}"
    }
    username = ''
    password = ''
    query = None  # for post json

    def __init__(self, auth_type='token', token=None, headers=None, username=None, password=None, query=None):
        self.auth_type = auth_type  # 'token', 'password'
        self.base_url = self.__class__.base_url
        self.query = query or self.__class__.query
        if self.auth_type == 'token':
            self.token = token or self.__class__.token
            self.headers = headers or self.__class__.headers
        elif self.auth_type == 'password':
            self.username = username or self.__class__.username
            self.password = password or self.__class__.password
            self.auth = (self.username, self.password)
        else:
            raise ValueError("auth_type must be in ['token', 'password'].")

    def request_get(self, url):
        if self.auth_type == 'token':
            response = requests.get(url, headers=self.headers)
        elif self.auth_type == 'password':
            response = requests.get(url, auth=self.auth)
        else:
            raise ValueError("auth_type must be in ['token', 'password'].")
        return response

    def request_post(self, base_url, query):
        self.query = query or self.query
        if self.auth_type == 'token':
            # print(base_url, self.query, self.headers)
            response = requests.post(base_url, json={'query': self.query}, headers=self.headers)
        elif self.auth_type == 'password':
            response = requests.post(base_url, json={'query': self.query}, auth=self.auth)
        else:
            raise ValueError("auth_type must be in ['token', 'password'].")
        return response

    def request(self, url, method='GET', retry=2, default_break=60, **kwargs):
        method = method.upper()
        while retry:
            try:
                if method == 'GET':
                    response = self.request_get(url)
                elif method == 'POST':
                    response = self.request_post(base_url=url, query=kwargs.get("query"))
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


class RequestGitHubAPI(RequestAPI):
    base_url = 'https://api.github.com/'
    url_pat_mode = 'name'
    token = GITHUB_TOKEN
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.4; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2225.0 Safari/537.36'
    }

    def __init__(self, url_pat_mode=None, *args):
        super().__init__(*args)
        self.url_pat_mode = url_pat_mode or self.__class__.url_pat_mode
        if self.url_pat_mode == 'id':
            self.user_url_pat = self.__class__.base_url + 'user/{account_id}'  # https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28#get-a-user-using-their-id
            self.repo_url_pat = self.__class__.base_url + 'repositories/{repo_id}'  # https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-public-repositories
        elif self.url_pat_mode == 'name':
            self.user_url_pat = self.__class__.base_url + 'users/{username}'  # https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28#get-a-user
            self.repo_url_pat = self.__class__.base_url + 'repos/{owner}/{repo}'  # https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#get-a-repository
        else:
            raise ValueError("url_pat_mode must be in ['id', 'name'].")
        self.commit_url_pat = self.repo_url_pat + '/git/commits/{commit_sha}'

    def get_url(self, url_type="repo_ext", ext_pat=None, params=None):
        url = None
        params = params or {}
        if url_type.startswith("user"):
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


class GitHubGraphQLAPI(RequestAPI):
    base_url = 'https://api.github.com/graphql'
    token = GITHUB_TOKEN
    headers = {
        'Authorization': 'bearer ' + token,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.4; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2225.0 Safari/537.36'
    }
    query = None

    def __init__(self, *args):
        super().__init__(*args)

    def request_post(self, query, base_url=None):
        self.base_url = base_url or self.base_url
        self.query = query or self.query
        return super().request_post(self.base_url, self.query)


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
    response = query_graphql_api.request_post(query_tags)
    data = response.json()
    print(data)
