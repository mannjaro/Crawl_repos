import datetime
import json
import os
import pickle
import subprocess
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
    df = df.set_index("project")
    # Clone to ./meta/clones/github.com pls

    if os.path.exists(os.path.normpath(os.path.join(cwd, "../.cache/contributor.pkl"))):
        with open(os.path.normpath(os.path.join(cwd, "../.cache/contributor.pkl")), 'rb') as f:
            df = pickle.load(f)
    else:
        df = get_contributors(df)
        with open(os.path.normpath(os.path.join(cwd, "../.cache/contributor.pkl")), 'wb') as f:
            pickle.dump(df, f)
    df = df.query("contributors > 1")
    df = get_loc(df)
    project = list(df.index)
    pd.DataFrame(project).to_csv(os.path.normpath(os.path.join(cwd, "../meta/clones/repo.csv")), index=False,
                                 header=False)
    concat(df)


def concat(chosen: pd.DataFrame):
    cwd = os.path.dirname(__file__)
    galaxy = pd.read_csv(os.path.normpath(os.path.join(cwd, "../meta/galaxy/galaxy_roles.csv")))
    chosen = chosen.assign(downloads=0, url="")
    galaxy = galaxy[["url", "downloads"]]
    for project, row in chosen.iterrows():
        query = 'url.str.contains("{}")'.format(project)
        chosen.at[project, 'downloads'] = galaxy.query(query, engine='python')["downloads"].values[0]
        chosen.at[project, 'url'] = galaxy.query(query, engine='python')["url"].values[0]
    chosen_path = os.path.normpath(os.path.join(cwd, "../out/summary.csv"))
    chosen["contributors"] = chosen["contributors"].astype("int")
    chosen.sort_values("downloads", ascending=False).to_csv(chosen_path)
    print("# Repository: {}".format(len(chosen)))


def get_contributors(df: pd.DataFrame):  # GitHub API v4 cannot get #contributor
    options = {
        "token": os.getenv("GITHUB_ACCESS_TOKEN")
    }
    api = GitHubAPIv3(options)

    df.assign(contributors=0)
    for project, row in df.iterrows():
        owner = str(project).split("/")[0]
        repo = str(project).split("/")[1]
        contributors = api.get_contributors(owner, repo, params={"anon": 1})
        df.at[project, "contributors"] = int(len(contributors))
        print("{} contributor: {}".format(project, len(contributors)))
    return df


def get_loc(df: pd.DataFrame):
    cwd = os.path.dirname(__file__)
    drop_list = []
    for item, row in df.iterrows():
        path = os.path.normpath(os.path.join(cwd, "../meta/clones/github.com/{}".format(item)))
        out = subprocess.run(["/opt/homebrew/bin/cloc", path, "--csv"], capture_output=True, text=True).stdout
        out = out.split("\n")[6:-1]
        yaml_count = [s for s in out if "YAML" in s][0].split(",")
        yaml_description = {
            "files": int(yaml_count[0]),
            "comment": int(yaml_count[3]),
            "code": int(yaml_count[4])
        }
        sum_count = [s for s in out if "SUM" in s][0].split(",")
        overall = {
            "files": int(sum_count[0]),
            "comment": int(sum_count[3]),
            "code": int(sum_count[4])
        }
        if overall["code"] < 100:
            drop_list.append(item)
            print("Dropped (LOC < 100): {}".format(item))
            continue
        if overall["comment"] < overall["code"] * 0.01:
            drop_list.append(item)
            print("Dropped (#Comment < 0.01%): {}".format(item))
            continue
        if yaml_description["files"] < overall["files"] * 0.1:
            drop_list.append(item)
            print("Dropped (.yaml < 0.1%): {}".format(item))
            continue
    return df.drop(drop_list)
