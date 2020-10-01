# Borg Backup Companion

The Borg Backup Companion allows you to easily backup your stuff in the Cloud.

100% secure - 100% open source - 100% full featured - 100% easy.

Using the full power of [Bitwarden](https://bitwarden.com),
[BorgBase](https://borgbase.com)... and [Docker](https://docker.com).

[![CodeFactor](https://www.codefactor.io/repository/github/kiwix/borg-backup/badge)](https://www.codefactor.io/repository/github/kiwix/borg-backup/)
[![Docker Build Status](https://img.shields.io/docker/cloud/build/kiwix/borg-backup)](https://hub.docker.com/r/kiwix/borg-backup)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

## Usage

### Setup new repository

Before starting a backup, we need to generate keys and save these in Bitwarden :

```bash
docker run -e BORGBASE_NAME=test_borg \
           -e BORGBASE_KEY=<borgbase_api_token> \
       kiwix/borg-backup setup-new-repo
```

With :

- `BORGBASE_NAME` : A name you choose for your repository. Must be unique in borgbase and not be used neither in bitwarden.
- `BORGBASE_KEY` : [BorgBase API token](https://www.borgbase.com/account?tab=2)

### Running backups

To backup files from `<backupdir>` folder (hourly, start a new container with:

```bash
docker run -d -v <backupdir>:/storage \
       -e BW_EMAIL=<your_bitwarden_login_mail> \
       -e BW_PASSWORD=<your_bitwarden_master_password> \
       -e BORGBASE_NAME=test_borg \
       -e BORGBASE_KEY=<borgbase_api_token> \
       kiwix/borg-backup
```

`BW_EMAIL` and `BW_PASSWORD` are your Bitwarden credentials.

### Backup a database

To backup a database you must specify the following as docker environment variables:

- `DB_TYPE` : `mysql` or `postgresql`
- `DB_NAME` : `all` to backup all databases on a host
- `DB_USERNAME`
- `DB_PASSWORD`
- `DB_HOSTNAME`
- `DB_PORT`

## Restoring a backup

### Prepare config

From your BitWarden account, get the public and private keys (username and password item).
Copy them in two files into your SSH dir (`$HOME/.ssh`), ex. `test_borg_id.pub` and `test_borg_id`.

[Install Borg Backup](https://borgbackup.readthedocs.io/en/stable/installation.html)


### List

From the [BorgBase UI](https://www.borgbase.com/repositories) (in *repositories*), copy your *repo path*. then:

```bash
borg list <repo_location>
```

Copy the name of archive that you want to restore, ex . `test_borg__backup__2020-09-27T12:33:22`

### Extract

Extract the archive :

```bash
borg extract <repo_location>::<archive>
```

Your backup is in `storage` directory.

## Author

Florent Kaisser <florent.pro@kaisser.name>


## License

[GPLv3](https://www.gnu.org/licenses/gpl-3.0) or later, see
[LICENSE](LICENSE) for more details.

