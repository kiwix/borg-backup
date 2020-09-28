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

Before run bakup, we need to generate keys and save these in Bitwarden :

```bash
docker run -e BORGBASE_NAME=test_borg \
           -e BORGBASE_KEY=<borgbase_api_token> \
       kiwix/borg-backup setup-new-repo
```

With :

- `BORGBASE_NAME` : The uniq identifier of your repository. This name must not already used for an other item in bitwarden.
- `BORGBASE_KEY` : BorgBase API token you can find your here : https://www.borgbase.com/account?tab=2

### Run backup

To backup files of `<barckupdir>` hourly with a new container :

```bash
docker run -d -v <barckupdir>:/storage \
       -e BW_EMAIL=<your_bitwarden_login_mail> \
       -e BW_PASSWORD=<your_bitwarden_master_password> \
       -e BORGBASE_NAME=test_borg \
       -e BORGBASE_KEY=<borgbase_api_token> \
       kiwix/borg-backup
```

`BW_EMAIL` and `BW_PASSWORD` is your Bitwarden crédential.

### Backup a database

To backup a database we must define :

- `DB_TYPE` : `mysql` or `postgresql`
- `DB_NAME` : `all` to backup all databases on a host
- `DB_USERNAME`
- `DB_PASSWORD`
- `DB_HOSTNAME`
- `DB_PORT`

## Restore backup

### Prepare config
From your BitWarden account, get the public and private keys (username and password item).
Copy them in two files into your SSH dir (`$HOME/.ssh`), ex. `test_borg_id.pub` and `test_borg_id`.

[Install Borg Backup](https://borgbackup.readthedocs.io/en/stable/installation.html)


### List
From your BorgBase account, find the repo location. You can copy this by click on first icon to left of repo name.
Lauch : 
```bash
borg list <repo_location>
```

Copy the name of archive that you want to restore, ex . `test_borg__backup__2020-09-27T12:33:22`

### Exract
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

