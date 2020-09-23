# borg-backup
Docker image for managing projects backup

## Usage

To backup files of `<barckupdir>` hourly with a new container :

```
docker run -d -v <barckupdir>:/storage  -e BW_EMAIL=<your_bitwarden_login_mail> -e BW_PASSWORD=<your_bitwarden_master_password> -e BORGBASE_NAME=test_borg -e BORGBASE_KEY=<borgbase_api_token> -ti backup-docker
```

### Backup a database

To backup a database we must define :

- DB_TYPE : mysql or postgresql
- DB_NAME
- DB_USERNAME 
- DB_PASSWORD

