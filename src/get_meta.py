import json
import os.path
import pickle
import csv
from datetime import datetime

import pandas as pd

from GitHub import GitHubAPIv4


def parse_meta(d: dict) -> dict:
    repository = d.get("repository")
    parsed_meta = {
        "createdAt": repository.get("createdAt"),
        "pushedAt": repository.get("pushedAt"),
        "releases": repository.get("releases").get("totalCount"),
        "issues": repository.get("issues").get("totalCount"),
    }
    commits = repository.get("defaultBranchRef")
    if commits is not None:
        commits = commits.get("target").get("history").get("totalCount")
    parsed_meta["commits"] = commits
    license_info = repository.get("licenseInfo")
    if license_info is not None:
        license_info = license_info.get("key")
    parsed_meta["license"] = license_info
    duration = \
        datetime.fromisoformat(parsed_meta["pushedAt"].replace('Z', '+00:00')) - \
        datetime.fromisoformat(parsed_meta["createdAt"].replace('Z', '+00:00'))
    month = int((duration.days / 365) * 12)

    if month != 0:
        parsed_meta["issue_rate"] = round(parsed_meta["issues"] / month, 3)
        parsed_meta["commit_rate"] = round(parsed_meta["commits"] / month, 3)
    else:
        parsed_meta["issue_rate"] = 0
        parsed_meta["commit_rate"] = 0
    return parsed_meta


def get_meta():
    api = GitHubAPIv4(os.getenv("GITHUB_ACCESS_TOKEN"))
    cwd = os.path.dirname(__file__)
    repo_name = []
    notfound = []
    meta_d = {}
    # Cacheの利用
    cache_notfound = os.path.normpath(os.path.join(cwd, "../.cache/notfound.pkl"))
    cache_meta = os.path.normpath(os.path.join(cwd, "../.cache/meta.pkl"))
    if not os.path.exists(os.path.normpath(os.path.join(cwd, "../out"))):
        os.makedirs(os.path.normpath(os.path.join(cwd, "../out")))
    if not os.path.exists(os.path.normpath(os.path.join(cwd, "../.cache"))):
        os.makedirs(os.path.normpath(os.path.join(cwd, "../.cache")))

    if os.path.exists(cache_meta):
        with open(cache_meta, "rb") as f:
            meta_d = pickle.load(f)
    if os.path.exists(cache_notfound):
        with open(cache_notfound, "rb") as f:
            notfound = pickle.load(f)

    reader = list(pd.read_csv(os.path.normpath(os.path.join(cwd, "../meta/galaxy/galaxy_roles.csv")))["url"].values)
    for value in reader:
        url = value.split("/")
        repo_name.append("/".join(url[3:]).removesuffix(".git"))
    if meta_d != {}:
        repo_name = list(set(repo_name) - set(meta_d.keys()))

    query = (
        """
query ($name: String!, $owner: String!) {
  repository(name: $name, owner: $owner) {
    createdAt
    pushedAt
    licenseInfo {
      key
    }
    releases {
      totalCount
    }
    issues {
      totalCount
    }
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: 0) {
            totalCount
          }
        }
      }
    }
  }
}
        """
    )

    for full_name in repo_name:
        owner = full_name.split("/")[0]
        name = full_name.split("/")[1]
        meta = api.call_query(query=query, params={"owner": owner, "name": name})
        if meta != {}:
            meta_d[full_name] = parse_meta(meta)
        else:
            notfound.append([full_name])
        with open(os.path.normpath(os.path.join(cwd, "../out/meta.json")), "w") as f:
            json.dump(meta_d, f, indent=4)
        with open(cache_meta, "wb") as f:
            pickle.dump(meta_d, f)
        if notfound:
            with open(os.path.normpath(os.path.join(cwd, "../out/notfound.csv")), "w") as f:
                writer = csv.writer(f, quoting=csv.QUOTE_ALL, delimiter=',')
                writer.writerows(notfound)
            with open(cache_notfound, "wb") as f:
                pickle.dump(notfound, f)
        print("Dump: [{}]".format(full_name))
