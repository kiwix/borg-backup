Kiwix's backup companion
===

A [docker image](https://hub.docker.com/r/kiwix/borg-backup) to easily backup your services' data into [BorgBase](https://www.borgbase.com/).

## What's this?

This tool is a docker image that you launch along your other docker services, sharing the data volume with it (read-only).

Example:

```sh
# running your imaginary service
docker run -v /data/www:/var/www/html -d nginx
# running your backup companion
docker run -v /data/www:/storage:ro kiwix/borg-backup backup --name nginx --every 1h
```

In this example, the content of `/data/www` on the host will be securely backed-up to BorgBase, in **append-only** mode, every hour.

## How it works

There are three main components to this tool:

- [BorgBase](https://www.borgbase.com/) is an affordable backup hosting service. We use it to store encrypted backups. You can use the free plan which is limited to two repositories or use a paid plan.
- [Bitwarden](https://bitwarden.com/) is a secured password management service. We only use features from the free plan.
- [Borg](https://www.borgbackup.org/) is an OSS backup tool that creates and transmits encrypted backups.

In borgbase, everything revolves around the concept of a *repo*. It's a place (~folder) in which your data goes (encrypted). For every *datasource* that you want to backup, you'll have one borgbase repo and one companion container.

This tool generates an SSH keypair for your repo, configures borgbase to allow backups using this key (append-only) and stores the keypair in your bitwarden account so you don't have to worry much about credentials.

## What do I need?

* One Borgbase account (free or paid)
* Two bitwarden accounts (a master one and a read-only one)

### Accounts setup

This is the annoying part. You'll have to manually create a couple of accounts and do some manipulations. This is a one-time thing, no matter how many repos you'll setup.

#### Borgbase

1. Create an account at [borgbase](https://www.borgbase.com/register) (or reuse one)
1. Once logged it, go to [Acounts » API](https://www.borgbase.com/account?tab=2) then **New Token**.
1. Choose a name (`kiwix-backup`?) and make sure you select **Create only** (important!)
1. Securely keep a reference to that created Token, you'll need that every time you setup a new repo.

#### Bitwarden

In order to store what we need in bitwarden (SSH keypairs, borgbase token) but without exposing our bitwarden token to the backup companion, we'll use two different accounts:

- one that is used solely to setup repo. That's the *master* account.
- one that is used when backing-up. this one will have read-only access to the items in the vault.

**Note**: using two accounts is safer but it doesn't mean the read-only account should be considered public. Keep it safe!

1. Create one master bitwarden account (email/password)
1. Create an *Organization* from that account's UI
1. Create a single *Collection* to be shared accross this organization
1. Invite a member to this organization, with:
 - the email adress you'll use to create that second bitwarden account in a minute
 - choosing `User` mode
 - choising `selected-collections only`
 - check the collection you created earlier
 - check `read-only` (but not hide password)
1. using the invitation link your received on that email address, create one backup bitwarden account (email/password)
1. login to bitwarden UI using master account and confirm membership

## Usage

Every *repo* or service you want to backup needs to be initialized once before you start backing-up your data.
This is a quick step that is separated from the backup one in order to keep your *master* bitwarden credentials from being moved around.

### Setting up

This command is intended to be run from your local machine so you don't have to insert your credentials on any other system.

This tool is **interactive** and will ask for your bitwarden master password and your borgbase token (both you should have created in *Accounts setup*).

```sh
docker run -it kiwix/borg-backup setup-new-repo \
    --name <repo-name> \
    --bitwarden <bitwarden-master-email> \
    --alert-days <nb-days>
    --quota <max-storage>
    --region <region>
```

#### Choosing a repo-name

We suggest you use reverse-FQDN notation for your repo names as the bitwarden matching is done using a *search* query meaning that if you have two repos named `my-service` and `my-service2`, the first one will fail, receiving two results instead of one.


**Optional values**:

- `<nb-days>`: periodicity of Borgbase e-mail alert in day(s) (default : `1`)
- `<max-storage>`:  quota in MB (default: no quota)
- `<region>`: borgbase server region (`eu` or `us`) (default : `eu`)

That's it. You should now have a *repo* ready to receive backups.

### Backing-up

The following is unattended and should be configured along your service. It runs forever, backing-up at the given interval.

```sh
docker run -v <some-folder>:/storage:ro \
    -e BITWARDEN_EMAIL=<bitwarden-readonly-email> \
    -e BITWARDEN_PASSWORD=<bitwarden-readonly-password> \
    kiwix/borg-backup backup --name <repo-name> --every <period>
```

- `<repo-name>` is the *repo* name configured in the setup step.
- `<period>` is the interval to launch backup on: units are `m` for minutes (`1-30`), `h` for hours (`1-30`), `d` for days (`1-14`), `M` for months (`1-6`).

Other parameters can be configured via docker environment variables:

- Retention options:
  - `KEEP_WITHIN`: keep all archives less than this old (no used by default)
  - `KEEP_DAILY`: keep last archive of this many latest days (default: `7`)
  - `KEEP_WEEKLY`: keep last archive of this many latest weeks (default: `5`)
  - `KEEP_MONTHLY`: keep last archive of this many latest months (default: `12`)
  - `KEEP_YEARLY`: keep last archive of this many latest years (default: `1`)
- Databases backup:
  - `DATABASES`: DSNs of the database to backup.

Database DSN should be in the form: `type://user:password@host:port/dbname`. It only supports `mysql` and `postgresql`. `dbname` can be `all` to backup all databases of that host/connexion.

**Note**: Bitwarden will send you a `New Device Logged In From Linux` email every time you launch that container.

## Restoring data

### Using the extract tool

Your backups are composed of *archives* or *versions* of your data. Use this tool to list and extract them with ease.

```sh
docker run \
    -v /data/temp:/restore:rw \
    -e BITWARDEN_EMAIL=<bitwarden-readonly-email> \
    -e BITWARDEN_PASSWORD=<bitwarden-readonly-password> \
    kiwix/borg-backup restore --name <repo-name> --list
```

This will list all the available archives. Note the name of the one you'll want to extract.

```sh
docker run \
    -v /data/temp:/restore:rw \
    -e BITWARDEN_EMAIL=<bitwarden-readonly-email> \
    -e BITWARDEN_PASSWORD=<bitwarden-readonly-password> \
    kiwix/borg-backup restore --name <repo-name> --extract "<archive-name>"
```

This will extract the content of the archive into `/restore` (which you should have mounted accordingly on the host).

`--extract` accepts a special value of `latest` that gets the lasted archive from the list.

### Manually

As your backup as just regular borg backups, you can follow [these docs](https://docs.borgbase.com/restore/) to restore your data manually.

Restoring requires your SSH keypair stored in bitwarden. In your bitwarden vault, you'll find one item for each of your *repo*. In this item, you'll find:

- `username`: that's your SSH public key. Save it as `~/.ssh/<myrepo>.pub`
- `password`: that's your SSH private key. Save it as `~/.ssh/<myrepo>`
- `BORGBASE_TOKEN`: that's your borgbase token. You don't need it for restoring.

You can now list, retrieve and extract any borg archive using regular tools.

## FAQ

### Can I specify multiple folders to backup?

Yes, just mount them as subfolders inside `/storage`:

```sh
docker run \
    -v /data/media/images:/storage/images:ro \
    -v /data/attachments:/storage/attachments:ro \
    kiwix/borg-backup backup --name myservice --every 1h
```

### Can I backup both a database and files at the same time?

Yes, if you specify `DATABASES` env, it's added on top of the mounted volume.

### Can I backup several databases at the same time?

Yes, beside the `all` trick mentionned above, if you need to backup a list of databases or databases on different hosts or of different kinds, just concatenate the DSNs into the `DATABASES` env, separating them with `|||`.

```
-e DATABASES="mysql://root:root@db:3306/all|||mysql://user:pass@prod:3306/clients"
```

### Can I replace BorgBase with another host?

No, at the moment, we use their API so it can't be replaced with another service.

### What if my bitwarden is compromised?

Don't panic! If your read-only bitwarden credentials are compromised, you won't loose any data:

- bitwarden items can't be modified by this account
- the SSH keypairs stored in bitwarden are now compromised but it can only do much on borgbase:
  - create new repo (check and delete those if that happened)
  - append new data to your repos (but cannot delete those you backed-up)

You should now manually remove the keypairs from borgbase and remove post-incident archives from your repo (read [this documentation on append-only](https://docs.borgbase.com/faq/#append-only-mode) first).

### Can I use a single bitwarden account?

Yes, but we highly discourage it.

The sole account is thus the read-write one (*master*) and it means it it gets compromised, one could delete items from your bitwarden account. As your SSH keypairs are only stored in bitwarden, loosing them mean you won't be able to retrieve nor decrypt your backups.
