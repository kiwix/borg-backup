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

os.environ["BORG_PASSPHRASE"] = ""  # nosec
os.environ["BORG_NEW_PASSPHRASE"] = ""  # nosec

CONFIG_DIR = "/root/"
BORG_ENCRYPTION = "repokey"
BORGMATIC_CONFIG = CONFIG_DIR + ".config/borgmatic/config.yaml"
DB_SEPARATOR = "|||"


def isAuthenticated(client):
    res = client.execute("{isAuthenticated}")
    return res["data"]["isAuthenticated"]


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


def create_repo(client, name, region, quota, alert):
    new_key_vars = {
        "name": "Key for " + name,
        "keyData": open(CONFIG_DIR + ".ssh/" + name + "_id.pub").readline().strip(),
    }
    res = client.execute(SSH_ADD, new_key_vars)
    new_key_id = res["data"]["sshAdd"]["keyAdded"]["id"]

    new_repo_vars = {
        "name": name,
        "appendOnlyKeys": [new_key_id],
        "region": region,
        "alertDays": alert,
        "quota": quota,
        "quotaEnabled": quota > 0,
    }
    res = client.execute(REPO_ADD, new_repo_vars)

    if res["data"]["repoAdd"]:
        return res["data"]["repoAdd"]["repoAdded"]["id"]

    print("Unable to create repository in BorgBase: ", end="")
    if "errors" in res and res["errors"]:
        return sys.exit(res["errors"][0]["message"])

    return exit("unknown error")


def write_config_databases(FILE, db_type, urls, options="", authentication_database=""):
    FILE.write(f"    {db_type}_databases:\n")
    for url in urls:
        db_name = url.path[1:]  # ignore initial "/"
        if not db_name:
            sys.exit("Incorrect database name")
        FILE.write(f"        - name: {db_name}\n")
        if url.username:
            FILE.write(f"          username : {url.username}\n")
        if url.password:
            FILE.write(f"          password : {url.password}\n")
        if url.hostname:
            FILE.write(f"          hostname : {url.hostname}\n")
        if url.port:
            FILE.write(f"          port : {url.port}\n")
        if options:
            FILE.write(f'          options : "{options}"\n')
        if authentication_database:
            FILE.write(
                f"          authentication_database: {authentication_database}\n"
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
    cross_fs_glob,
):

    # when backuping a database, the `one_file_system` option is automatically
    # turned on, preventing borgmatic from crossing mounted paths.
    # Adding a `*` glob does allow it for some reason but the counter part is that
    # it won't backup hidden files and folders on root of /storage.
    # See: https://torsion.org/borgmatic/docs/reference/configuration/
    folder_star = "*" if databases and cross_fs_glob else ""

    FILE.write(
        f"""location:
    source_directories:
        - /storage/{folder_star}
    repositories:
        - {repo_path}
storage:
    encryption_passphrase: ""
    relocated_repo_access_is_ok: true
    unknown_unencrypted_repo_access_is_ok: true
    borg_base_directory: "/repo"
    borg_cache_directory: "/cache"
    archive_name_format: '{name}__backup__{{now}}'
"""
    )
    if (
        int(keep_within[:-1]) > 0
        or keep_daily > 0
        or keep_weekly > 0
        or keep_monthly > 0
        or keep_yearly > 0
    ):
        FILE.write("retention:\n")
        if int(keep_within[:-1]) > 0:
            FILE.write(f"    keep_within: {keep_within}\n")
        if keep_daily > 0:
            FILE.write(f"    keep_daily: {keep_daily}\n")
        if keep_weekly > 0:
            FILE.write(f"    keep_weekly: {keep_weekly}\n")
        if keep_monthly > 0:
            FILE.write(f"    keep_monthly: {keep_monthly}\n")
        if keep_yearly > 0:
            FILE.write(f"    keep_yearly: {keep_yearly}\n")
        FILE.write(f"    prefix: {name}__backup__\n")

    databases_mysql = list(filter(lambda u: u.scheme == "mysql", databases))
    databases_postgresql = list(filter(lambda u: u.scheme == "postgresql", databases))
    databases_mongodb = list(filter(lambda u: u.scheme == "mongodb", databases))

    if databases_mysql or databases_postgresql or databases_mongodb:
        FILE.write("hooks:\n")
        if databases_mysql:
            write_config_databases(
                FILE,
                "mysql",
                databases_mysql,
                "--single-transaction --quick --lock-tables=false "
                "--max-allowed-packet=128M",
            )
        if databases_postgresql:
            write_config_databases(FILE, "postgresql", databases_postgresql)
        if databases_mongodb:
            write_config_databases(
                FILE, "mongodb", databases_mongodb, authentication_database="admin"
            )


def main(
    borgbase_api_client,
    name,
    know_hosts_file,
    keep_within,
    keep_daily,
    keep_weekly,
    keep_monthly,
    keep_yearly,
    region,
    quota,
    alert,
    databases,
    cross_fs_glob,
    max_retry,
    initial_delay_retry,
):
    if not isAuthenticated(borgbase_api_client):
        print("Unable to connect to your Borgbase account, please check your token.")
        return 2

    repo_id = repo_exists(borgbase_api_client, name)

    if repo_id:
        print("Repo exists with name", name)
    else:
        print("Repo not exists with name", name, ", create it ...")
        repo_id = create_repo(borgbase_api_client, name, region, quota, alert)

    hostname = repo_hostname(borgbase_api_client, repo_id)
    repo_path = repo_id + "@" + hostname + ":repo"
    print("Use repo path :", repo_path)

    with open(KNOWN_HOSTS_FILE, "w") as outfile:
        subprocess.run(["/usr/bin/env", "ssh-keyscan", "-H", hostname], stdout=outfile)

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
            cross_fs_glob,
        )

    if max_retry == 0:
        # just create conf file, not run Borgmatic
        return 0

    print("Init Borgmatic ...")

    retry = max_retry
    delay = initial_delay_retry
    while retry > 0:
        # gives time for server init and try again if needed
        print(f"Waiting for borgbase to create repository ({delay}s)...")
        time.sleep(delay)
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
            print("Successfully created repository!")
            return 0
        retry = retry - 1
        delay = delay * 2
    print(f"Cannot init backup (error {ret}), check your Borgbase account")


if __name__ == "__main__":
    TOKEN = os.environ.get("BORGBASE_KEY")
    BACKUP_NAME = os.environ.get("BORGBASE_NAME")
    KNOWN_HOSTS_FILE = os.environ.get("KNOWN_HOSTS_FILE")

    DATABASES = os.environ.get("DATABASES")
    CROSS_FS_GLOB = os.environ.get("CROSS_FS_GLOB")

    KEEP_WITHIN = os.environ.get("KEEP_WITHIN")
    KEEP_DAILY = int(os.environ.get("KEEP_DAILY"))
    KEEP_WEEKLY = int(os.environ.get("KEEP_WEEKLY"))
    KEEP_MONTHLY = int(os.environ.get("KEEP_MONTHLY"))
    KEEP_YEARLY = int(os.environ.get("KEEP_YEARLY"))

    MAX_BORGMATIC_RETRY = int(os.environ.get("MAX_BORGMATIC_RETRY"))
    WAIT_BEFORE_BORGMATIC_RETRY = int(os.environ.get("WAIT_BEFORE_BORGMATIC_RETRY"))
    QUOTA = int(os.environ.get("QUOTA"))
    ALERT = int(os.environ.get("ALERT"))
    REGION = os.environ.get("REGION")

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
                REGION,
                QUOTA,
                ALERT,
                list(map(urlparse, DATABASES.split(DB_SEPARATOR))) if DATABASES else [],
                bool(CROSS_FS_GLOB),
                MAX_BORGMATIC_RETRY,
                WAIT_BEFORE_BORGMATIC_RETRY,
            )
        )
    else:
        sys.exit(
            "Environnement variables missing, check BORGBASE_KEY, BORGBASE_NAME, "
            "KNOWN_HOSTS_FILE and KEEP_*"
        )
