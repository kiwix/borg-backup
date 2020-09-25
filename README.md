Borg Backup Companion
=====================

The Borg Backup Companion allows you to easily backup your stuff in the Cloud.

100% secure - 100% open source - 100% full featured - 100% easy.

Using the full power of [Bitwarden](https://bitwarden.com),
[BorgBase](https://borgbase.com)... and [Docker](https://docker.com).

[![CodeFactor](https://www.codefactor.io/repository/github/kiwix/borg-backup/badge)](https://www.codefactor.io/repository/github/kiwix/borg-backup/)
[![Docker Build Status](https://img.shields.io/docker/cloud/build/kiwix/borg-backup)](https://hub.docker.com/r/kiwix/borg-backup)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Usage
-----

To backup files of `<barckupdir>` hourly with a new container :

```bash
docker run -d -v <barckupdir>:/storage \
       -e BW_EMAIL=<your_bitwarden_login_mail> \
       -e BW_PASSWORD=<your_bitwarden_master_password> \
       -e BORGBASE_NAME=test_borg \
       -e BORGBASE_KEY=<borgbase_api_token> \
       -ti backup-docker
```

License
-------

[GPLv3](https://www.gnu.org/licenses/gpl-3.0) or later, see
[LICENSE](LICENSE) for more details.