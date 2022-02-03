import json
import os
from collections import Counter

from GitHub import GitHubAPIv4
import pandas as pd


def get_label():
    cwd = os.path.dirname(__file__)
    api = GitHubAPIv4(os.getenv("GITHUB_ACCESS_TOKEN"))
    query = """
query ($name: String!, $owner: String!, $cursor: String) {
  repository(name: $name, owner: $owner) {
    labels(first: 50, after: $cursor) {
      edges {
        node {
          name
        }
      }
      pageInfo {
        endCursor
        hasNextPage
      }
    }
  }
}"""
    all_label = []
    c = {}
    repositories = pd.read_csv(os.path.normpath(os.path.join(cwd, "../meta/clones/repo.csv")), header=None).values
    for item in repositories:
        item = item[0].split("/")
        params = {
            "owner": item[0],
            "name": item[1]
        }
        json_obj = api.call_query(query, params)
        labels = json_obj.get("repository").get("labels").get("edges")
        for label in labels:
            all_label.append(label.get("node").get("name"))
        page_info = json_obj.get("repository").get("labels").get("pageInfo")
        while page_info.get("hasNextPage"):
            params["cursor"] = page_info.get("endCursor")
            obj = api.call_query(query, params)
            for label in labels:
                all_label.append(label.get("node").get("name"))
            page_info = obj.get("repository").get("labels").get("pageInfo")
        c = dict(Counter(all_label))
        with open(os.path.normpath(os.path.join(cwd, "../out/labels.json")), 'w') as f:
            json.dump(c, f, indent=4)
