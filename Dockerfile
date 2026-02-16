FROM debian:trixie-slim
LABEL org.opencontainers.image.source=https://github.com/kiwix/borg-backup
#
# Author : Florent Kaisser <florent.pro@kaisser.name>
#
LABEL maintainer="kiwix"

# Retention options
ENV KEEP_WITHIN="0H"
ENV KEEP_DAILY="7"
ENV KEEP_WEEKLY="5"
ENV KEEP_MONTHLY="12"
ENV KEEP_YEARLY="1"
# Quota on Borgbase account in Mo, non quota by default (0)
ENV QUOTA="0"
# server region (eu or us)
ENV REGION="eu"
# Periodicity of Borgbase e-mail alert in day(s)
ENV ALERT="1"
# The interval to launch backup on: units are m for minutes, h for hours, d for days, M for months
ENV PERIODICITY="1d"
# Day, hour and minute to which the backup is run
ENV BACKUP_DAY=1
ENV BACKUP_HOUR=3
ENV BACKUP_MINUTE=12
# No database to backup in default
ENV DATABASES=""
# options to pass to the database hook
ENV DATABASES_OPTIONS=""
# Retry paramaeters when setup a new repo
ENV MAX_BORGMATIC_RETRY="10"
ENV WAIT_BEFORE_BORGMATIC_RETRY="30"
# for k8s cluster data backup
ARG KUBECTL_VERSION="1.34.2"

RUN apt-get update && \
    apt-get install -y --no-install-recommends bash curl borgbackup vim \
        python3 python3-pip python3-setuptools openssh-client unzip git cron \
        default-mysql-client ca-certificates \
        dnsutils bind9utils tar xz-utils gzip bzip2 coreutils grep lsb-release gnupg2 \
        python3.13-venv && \
    install -d /usr/share/postgresql-common/pgdg && \
    curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc && \
    . /etc/os-release && \
    sh -c "echo 'deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $VERSION_CODENAME-pgdg main' > /etc/apt/sources.list.d/pgdg.list" && \
    apt-get update && \
    apt-get install -y --no-install-recommends -y postgresql-client-18 && \
    curl -Ls https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian12-x86_64-100.14.1.deb -o mongo-tools.deb && \
    apt-get install -y --no-install-recommends -y ./mongo-tools.deb && \
    rm -f ./mongo-tools.deb && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/* && \
    curl -Ls 'https://github.com/bitwarden/cli/releases/download/v1.22.1/bw-linux-1.22.1.zip' -o bitwarden.zip && \
    unzip bitwarden.zip && rm -f bitwarden.zip && chmod +x bw && mv bw /usr/local/bin/ && \
    git clone --depth=1 --branch=master https://github.com/borgbase/borgbase-api-client.git && \
    mv borgbase-api-client/borgbase_api_client/ /usr/lib/python3/dist-packages/ && \
    rm -rf borgbase-api-client && \
    python3.13 -m venv /app/kiwix-python && \
    . /app/kiwix-python/bin/activate && \
    pip3 install --no-cache-dir --upgrade requests==2.27.1 borgmatic==1.5.24 jsonschema==4.4.0 pyrsistent==0.18.1  && \
    curl -sLo /usr/bin/jq "https://github.com/jqlang/jq/releases/download/jq-1.8.1/jq-linux64" && \
    chmod +x /usr/bin/jq && \
    curl -sLo /usr/bin/yq "https://github.com/mikefarah/yq/releases/download/v4.52.4/yq_linux_amd64" && \
    chmod +x /usr/bin/yq && \
    curl -sLo /usr/bin/kubectl \
    "https://storage.googleapis.com/kubernetes-release/release/v$KUBECTL_VERSION/bin/linux/amd64/kubectl" && \
    chmod +x /usr/bin/kubectl && \
    curl -sLo /usr/bin/kube-dump "https://raw.githubusercontent.com/WoozyMasta/kube-dump/1.1.2/kube-dump" && \
    chmod +x /usr/bin/kube-dump

# Entrypoint for k8s mode
COPY entrypoint.sh /usr/bin/entrypoint
RUN chmod +x /usr/bin/entrypoint
# Install scripts
COPY bin/ /usr/local/bin/
RUN chmod -R 0500 /usr/local/bin/*

WORKDIR /root

RUN mkdir -p .ssh .config/borgmatic/ /config /storage /restore

ENTRYPOINT ["/usr/bin/entrypoint"]
CMD ["backup"]
