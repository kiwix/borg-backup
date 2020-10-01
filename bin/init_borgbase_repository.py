#!/usr/bin/python3
#
# Author : Florent Kaisser <florent.pro@kaisser.name>
#

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
MAX_BORGMATIC_RERTY = 5

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
    db_type,
    db_name,
    db_username,
    db_password,
    db_hostname,
    db_port,
):
    repo_id = repo_exists(borgbase_api_client, name)

    if repo_id:
        print("Repo exists with name", name)
    else:
        print("Repo not exists with name", name, ", create it ...")
        repo_id = create_repo(borgbase_api_client, name)

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

        if (db_type == "postgresql" or db_type == "mysql") and db_name:
            FILE.write(
                f"""
    hooks:
        {db_type}_databases:
            - name: {db_name}
              username : {db_username}
              password : {db_password}
              hostname : {db_hostname}
              port : {db_port}
    """
            )

    print("Init Borgmatic ...")

    retry = MAX_BORGMATIC_RERTY
    while retry > 0:
        #gives time for server init and try again if needed
        time.sleep(2)
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
        if ret == 0 :
            return 0
        else:
            retry = retry - 1
            print("Borgmatic init has failed, retry again ...")
    print("Cannot init backup, check your Borgbase account")

if __name__ == "__main__":
    TOKEN = os.environ.get("BORGBASE_KEY")
    BACKUP_NAME = os.environ.get("BORGBASE_NAME")
    KNOWN_HOSTS_FILE = os.environ.get("KNOWN_HOSTS_FILE")

    KEEP_WITHIN = os.environ.get("KEEP_WITHIN")
    KEEP_DAILY = os.environ.get("KEEP_DAILY")
    KEEP_WEEKLY = os.environ.get("KEEP_WEEKLY")
    KEEP_MONTHLY = os.environ.get("KEEP_MONTHLY")
    KEEP_YEARLY = os.environ.get("KEEP_YEARLY")

    DB_TYPE = os.environ.get("DB_TYPE")
    DB_NAME = os.environ.get("DB_NAME")
    DB_USERNAME = os.environ.get("DB_USERNAME")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    DB_HOSTNAME = os.environ.get("DB_HOSTNAME")
    DB_PORT = os.environ.get("DB_PORT")

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
                    DB_TYPE,
                    DB_NAME,
                    DB_USERNAME,
                    DB_PASSWORD,
                    DB_HOSTNAME,
                    DB_PORT,
                )
            )
        except Exception as e:
            print("Cannot connect to BorgBase :", e)
            exit(2)
    else:
        sys.exit(
            "Environnement variables missing, check BORGBASE_KEY, BORGBASE_NAME, KNOWN_HOSTS_FILE and KEEP_*"
        )
