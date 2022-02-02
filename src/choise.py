import datetime
import json
import os
from GitHub import GitHubAPIv3

import pandas as pd


def check():
    cwd = os.path.dirname(__file__)
    meta_path = os.path.normpath(os.path.join(cwd, "../out/meta.json"))
    with open(meta_path, "r") as f:
        meta = json.load(f)
    # Select rules (see https://www.notion.so/c305723fa96240e5867a87c21d711e18)
    # Push events: Pushed Default branch in 6 month
    # Releases: 2 more releases
    # Commit ratio: 2 or more commits in month in average
    # Issue ratio: 0.01 or more issues in month in average
    # Is licensed: Repository can be surveyed

    rules = {
        "push_events": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=0))),
        "releases": 1,
        "commit_ratio": 2,
        "issue_ratio": 0.01,
    }
    store = []
    for key, value in meta.items():
        delta = rules["push_events"] - datetime.datetime.fromisoformat(value["pushedAt"].replace("Z", "+00:00"))
        if delta.days > 6 * 30:
            continue
        if rules["releases"] > value.get("releases"):
            continue
        if rules["commit_ratio"] > value.get("commit_rate"):
            continue
        if rules["issue_ratio"] > value.get("issue_rate"):
            continue
        if value.get("license") is None:
            continue
        tmp = [key]
        tmp.extend(list(value.values()))
        store.append(tmp)
    df = pd.DataFrame(store, columns=["project", "createdAt", "pushedAt", "releases", "issues", "commits", "license",
                                      "issue_rate", "commit_rate"])

    # Clone to ./meta/clones/github.com pls
    if os.path.exists(os.path.normpath(os.path.join(cwd, "../out/chosen.csv"))):
        df = pd.read_csv(os.path.normpath(os.path.join(cwd, "../out/chosen.csv")))
    else:
        df = get_contributors(df)
    df = df.query("contributors > 1")
    df["project"].to_csv(os.path.normpath(os.path.join(cwd, "../meta/clones/repo.csv")), index=False, header=False)
    concat(df)


def concat(chosen: pd.DataFrame):
    cwd = os.path.dirname(__file__)
    galaxy = pd.read_csv(os.path.normpath(os.path.join(cwd, "../meta/galaxy/galaxy_roles.csv")))
    chosen = chosen.assign(downloads=0, url="")
    galaxy = galaxy[["url", "downloads"]]
    for index, row in chosen.iterrows():
        project = row["project"]
        query = 'url.str.contains("{}")'.format(project)
        chosen.at[index, 'downloads'] = galaxy.query(query, engine='python')["downloads"].values[0]
        chosen.at[index, 'url'] = galaxy.query(query, engine='python')["url"].values[0]
    chosen_path = os.path.normpath(os.path.join(cwd, "../out/chosen.csv"))
    chosen["contributors"] = chosen["contributors"].astype("int")
    chosen.sort_values("downloads", ascending=False).to_csv(chosen_path, index=False)
    print("# Repository: {}".format(len(chosen)))


def get_contributors(df: pd.DataFrame):  # GitHub API v4 cannot get #contributor
    options = {
        "token": os.getenv("GITHUB_ACCESS_TOKEN")
    }
    api = GitHubAPIv3(options)

    df.assign(contributors=0)
    for index, row in df.iterrows():
        project = row["project"]
        owner = project.split("/")[0]
        repo = project.split("/")[1]
        contributors = api.get_contributors(owner, repo, params={"anon": 1})
        df.at[index, "contributors"] = int(len(contributors))
        print("{} contributor: {}".format(project, len(contributors)))
    return df
