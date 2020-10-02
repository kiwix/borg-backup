#!/usr/bin/python3
#
# Author : Florent Kaisser <florent.pro@kaisser.name>
#

from borgbase_api_client.client import GraphQLClient
from borgbase_api_client.mutations import REPO_ADD, SSH_ADD
from urllib.parse import urlparse
import os
import sys
import subprocess
import time

os.environ["BORG_PASSPHRASE"] = ""
os.environ["BORG_NEW_PASSPHRASE"] = ""

CONFIG_DIR = "/root/"
BORG_ENCRYPTION = "repokey"
BORGMATIC_CONFIG = CONFIG_DIR + ".config/borgmatic/config.yaml"
DB_SEPARATOR="|||"

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


def write_config_databases(FILE, db_type, urls):
    # if (db_type == "postgresql" or db_type == "mysql") and db_name:
    FILE.write(
        f"""
        {db_type}_databases:"""
    )
    for url in urls:
        db_name = url.path[1:]  # ignore initial "/"
        if not db_name:
            sys.exit("Incorrect database name")
        FILE.write(
            f"""
            - name: {db_name}"""
        )
        if url.username:
            FILE.write(
                f"""
              username : {url.username}"""
            )
        if url.password:
            FILE.write(
                f"""
              password : {url.password}"""
            )
        if url.hostname:
            FILE.write(
                f"""
              hostname : {url.hostname}"""
            )
        if url.port:
            FILE.write(
                f"""
              port : {url.port}"""
            )


def write_config(
    FILE,
    name,
    repo_path,
    keep_within,
    keep_daily,
    keep_weekly,
    keep_monthly,
    keep_yearly,
    databases,
):

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

    databases_mysql = list(filter(lambda u: u.scheme == "mysql", databases))
    databases_postgresql = list(filter(lambda u: u.scheme == "postgresql", databases))

    if databases_mysql or databases_postgresql:
        FILE.write("    hooks:")
        if databases_mysql:
            write_config_databases(FILE, "mysql", databases_mysql)
        if databases_postgresql:
            write_config_databases(FILE, "postgresql", databases_postgresql)


def main(
    borgbase_api_client,
    name,
    know_hosts_file,
    keep_within,
    keep_daily,
    keep_weekly,
    keep_monthly,
    keep_yearly,
    databases,
    max_retry,
    wait_retry
):
    repo_id = repo_exists(borgbase_api_client, name)

    if repo_id:
        print("Repo exists with name", name)
    else:
        print("Repo not exists with name", name, ", create it ...")
        repo_id = create_repo(borgbase_api_client, name)

    hostname = repo_hostname(borgbase_api_client, repo_id)
    repo_path = repo_id + "@" + hostname + ":repo"
    print("Use repo path :", repo_path)

    with open(KNOWN_HOSTS_FILE, "w") as outfile:
        subprocess.run(["ssh-keyscan", "-H", hostname], stdout=outfile)

    with open(BORGMATIC_CONFIG, "w") as FILE:
        write_config(
            FILE,
            name,
            repo_path,
            keep_within,
            keep_daily,
            keep_weekly,
            keep_monthly,
            keep_yearly,
            databases,
        )

    if max_retry == 0:
        #just create conf file, not run Borgmatic
        exit(0)

    print("Init Borgmatic ...")

    retry = max_retry
    while retry > 0:
        # gives time for server init and try again if needed
        time.sleep(wait_retry)
        ret = subprocess.call(
            [
                "/usr/local/bin/borgmatic",
                "-c",
                BORGMATIC_CONFIG,
                "-v",
                "1",
                "init",
                "--encryption",
                BORG_ENCRYPTION,
            ]
        )
        if ret == 0:
            return 0
        else:
            retry = retry - 1
            print("Borgmatic init has failed, retry again ...")
    print("Cannot init backup, check your Borgbase account")


if __name__ == "__main__":
    TOKEN = os.environ.get("BORGBASE_KEY")
    BACKUP_NAME = os.environ.get("BORGBASE_NAME")
    KNOWN_HOSTS_FILE = os.environ.get("KNOWN_HOSTS_FILE")

    DATABASES = os.environ.get("DATABASES")

    KEEP_WITHIN = os.environ.get("KEEP_WITHIN")
    KEEP_DAILY = os.environ.get("KEEP_DAILY")
    KEEP_WEEKLY = os.environ.get("KEEP_WEEKLY")
    KEEP_MONTHLY = os.environ.get("KEEP_MONTHLY")
    KEEP_YEARLY = os.environ.get("KEEP_YEARLY")

    MAX_BORGMATIC_RETRY = int(os.environ.get("MAX_BORGMATIC_RETRY"))
    WAIT_BEFORE_BORGMATIC_RETRY = int(os.environ.get("WAIT_BEFORE_BORGMATIC_RETRY"))

    if (
        TOKEN
        and BACKUP_NAME
        and KNOWN_HOSTS_FILE
        and KEEP_WITHIN
        and KEEP_DAILY
        and KEEP_WEEKLY
        and KEEP_MONTHLY
        and KEEP_YEARLY
    ):
        try:
            sys.exit(
                main(
                    GraphQLClient(TOKEN),
                    BACKUP_NAME,
                    KNOWN_HOSTS_FILE,
                    KEEP_WITHIN,
                    KEEP_DAILY,
                    KEEP_WEEKLY,
                    KEEP_MONTHLY,
                    KEEP_YEARLY,
                    list(map(urlparse, DATABASES.split(DB_SEPARATOR))) if urlparse else [],
                    MAX_BORGMATIC_RETRY,
                    WAIT_BEFORE_BORGMATIC_RETRY
                )
            )
        except Exception as e:
            print("Cannot connect to BorgBase :", e)
            exit(2)
    else:
        sys.exit(
            "Environnement variables missing, check BORGBASE_KEY, BORGBASE_NAME, KNOWN_HOSTS_FILE and KEEP_*"
        )
