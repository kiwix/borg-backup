#!/usr/bin/python3
from borgbase_api_client.client import GraphQLClient
from borgbase_api_client.mutations import REPO_ADD, SSH_ADD
import os
import sys
import subprocess
import time

os.environ["BORG_PASSPHRASE"] = ""
os.environ["BORG_NEW_PASSPHRASE"] = ""

CONFIG_DIR = "/root/"
BORG_ENCRYPTION = "repokey"
BORGMATIC_CONFIG = CONFIG_DIR + ".config/borgmatic/config.yaml"


def repo_exists(client, name):
    query = """
    {
      repoList {
        id
        name
      }
    }
    """
    res = client.execute(query)
    for repo in res["data"]["repoList"]:
        if repo["name"] == name:
            return repo["id"]

    return ""


def repo_hostname(client, repo_id):
    query = """
    {
      repoList {
        id
        name
        server {
          hostname
        }
      }
    }
    """
    res = client.execute(query)
    for repo in res["data"]["repoList"]:
        if repo["id"] == repo_id:
            return repo["server"]["hostname"]


def create_repo(client, name):
    new_key_vars = {
        "name": "Key for " + name,
        "keyData": open(CONFIG_DIR + ".ssh/" + name + "_id.pub").readline().strip(),
    }
    res = client.execute(SSH_ADD, new_key_vars)
    new_key_id = res["data"]["sshAdd"]["keyAdded"]["id"]

    new_repo_vars = {
        "name": name,
        "quotaEnabled": False,
        "appendOnlyKeys": [new_key_id],
        "region": "eu",
        "alertDays": 1,
        "quota": 2048,
        "quotaEnabled": True,
    }
    res = client.execute(REPO_ADD, new_repo_vars)

    return res["data"]["repoAdd"]["repoAdded"]["id"]


def main(
    borgbase_api_client,
    name,
    know_hosts_file,
    keep_within,
    keep_daily,
    keep_weekly,
    keep_monthly,
    keep_yearly,
):
    repo_id = repo_exists(borgbase_api_client, name)

    if repo_id:
        print("Repo exists with name", name)
    else:
        print("Repo not exists with name", name, ", create it ...")
        repo_id = create_repo(borgbase_api_client, name)
        # waiting a couple of second to prevent borgmatic fail
        time.sleep(2)

    hostname = repo_hostname(borgbase_api_client, repo_id)
    repo_path = repo_id + "@" + hostname + ":repo"

    with open(KNOWN_HOSTS_FILE, "w") as outfile:
        subprocess.run(["ssh-keyscan", "-H", hostname], stdout=outfile)

    print("Use repo path :", repo_path)

    with open(BORGMATIC_CONFIG, "w") as FILE:
        FILE.write(
            f"""
    location:
        source_directories:
            - /storage
        repositories:
            - {repo_path}
    storage:
        encryption_passphrase: ""
        relocated_repo_access_is_ok: true
        unknown_unencrypted_repo_access_is_ok: true
        borg_base_directory: "/repo"
        borg_cache_directory: "/cache"
        archive_name_format: '{name}__backup__{{now}}'
    retention:
        keep_within: {keep_within}
        keep_daily: {keep_daily}
        keep_weekly: {keep_weekly}
        keep_monthly: {keep_monthly}
        keep_yearly: {keep_yearly}
        prefix: {name}__backup__
    """
        )

    print("Init Borgmatic ...")
    subprocess.call(
        [
            "borgmatic",
            "-c",
            BORGMATIC_CONFIG,
            "-v",
            "1",
            "init",
            "--encryption",
            BORG_ENCRYPTION,
        ]
    )


if __name__ == "__main__":
    TOKEN = os.environ.get("BORGBASE_KEY")
    # MYSQL_USER = os.environ.get("MYSQL_USER")
    # MYSQL_DB = os.environ.get("MYSQL_DB")
    BACKUP_NAME = os.environ.get("BORGBASE_NAME")
    KNOWN_HOSTS_FILE = os.environ.get("KNOWN_HOSTS_FILE")

    KEEP_WITHIN = os.environ.get("KEEP_WITHIN")
    KEEP_DAILY = os.environ.get("KEEP_DAILY")
    KEEP_WEEKLY = os.environ.get("KEEP_WEEKLY")
    KEEP_MONTHLY = os.environ.get("KEEP_MONTHLY")
    KEEP_YEARLY = os.environ.get("KEEP_YEARLY")

    if TOKEN and BACKUP_NAME and KNOWN_HOSTS_FILE:
        main(
            GraphQLClient(TOKEN),
            BACKUP_NAME,
            KNOWN_HOSTS_FILE,
            KEEP_WITHIN,
            KEEP_DAILY,
            KEEP_WEEKLY,
            KEEP_MONTHLY,
            KEEP_YEARLY,
        )
    else:
        sys.exit(
            "Environnement variables missing, check BORGBASE_KEY, BORGBASE_NAME and KNOWN_HOSTS_FILE"
        )
