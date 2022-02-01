import sys
import urllib.request
import re
from urllib.error import URLError
from urllib.parse import quote, urlencode
import json


class GitHubREST:
    BASE_URL = "https://api.github.com"

    def __init__(self, option=None):
        if option is None:
            option = {}
        self.option = option

    def __get_json(self, url, paginate=False):
        req = self.__create_request(url)
        try:
            with urllib.request.urlopen(req) as res:
                json_text = res.read().decode('utf-8')
                json_obj = json.loads(json_text)
                # ページネーションによる繰り返し取得
                if paginate:
                    next_link = self.__get_next_link(res.info())
                    if next_link:
                        json_obj.extend(self.__get_json(next_link, paginate=True))
                return json_obj
        except URLError as err:
            print('Could not access: %s' % req.full_url, file=sys.stderr)
            print(err, file=sys.stderr)
            sys.exit(1)

    # ページネーションによる連続取得が必要な場合は、
    # 次のアドレスを返す。必要ない場合は None を返す。
    def __get_next_link(self, response_headers):
        link = response_headers['Link']
        if not link:
            return None
        match = re.search(r'<(\S+)>; rel="next"', link)
        if match:
            return match.group(1)
        return None

    def __create_request(self, url):
        req = urllib.request.Request(url)
        if 'token' in self.option:
            req.add_header('Authorization', 'token %s' % self.option['token'])
        if 'proxy' in self.option:
            req.set_proxy(self.option['proxy'], 'http')
            req.set_proxy(self.option['proxy'], 'https')
        return req

    def get_contributors(self, owner, repo, params):
        url = self.BASE_URL + '/repos/{0}/{1}/contributors?per_page=100'.format(owner, repo)
        if params:
            url = '{0}&{1}'.format(url, urlencode(params))
        return self.__get_json(url, paginate=True)
