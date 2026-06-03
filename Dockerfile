FROM debian:trixie-slim
LABEL org.opencontainers.image.source=https://github.com/kiwix/borg-backup
LABEL maintainer="kiwix"

# TARGETPLATFORM is injected by docker build
ARG TARGETPLATFORM

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

RUN echo "TARGETPLATFORM: $TARGETPLATFORM" \
    && if [ "$TARGETPLATFORM" = "linux/arm64/v8" \
         -o "$TARGETPLATFORM" = "linux/arm64" ]; then AARCH="aarch64"; ARCH="arm64"; MARCH="arm64"; BARCH="-arm64"; \
       elif [ "$TARGETPLATFORM" = "linux/amd64/v3" \
         -o "$TARGETPLATFORM" = "linux/amd64/v2" \
         -o "$TARGETPLATFORM" = "linux/amd64" ]; then AARCH="x86_64"; ARCH="amd64"; MARCH="x86_64"; BARCH=""; \
       # we dont suppot any other arch so let it fail
       else ARCH="unknown"; AARCH="unknown"; fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends bash curl borgbackup vim \
        python3 python3-pip python3-setuptools openssh-client unzip git cron \
        default-mysql-client ca-certificates \
        dnsutils bind9utils tar xz-utils gzip bzip2 coreutils grep lsb-release gnupg2 \
        jq yq \
        python3.13-venv \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && . /etc/os-release \
    && sh -c "echo 'deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $VERSION_CODENAME-pgdg main' > /etc/apt/sources.list.d/pgdg.list" \
    && apt-get update \
    && apt-get install -y --no-install-recommends -y postgresql-client-18 \
    && curl -Ls https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu2404-${MARCH}-100.17.0.deb -o mongo-tools.deb \
    && apt-get install -y --no-install-recommends -y ./mongo-tools.deb \
    && rm -f ./mongo-tools.deb \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/* \
    && curl -Ls https://github.com/bitwarden/clients/releases/download/cli-v2026.5.0/bw-oss-linux${BARCH}-2026.5.0.zip -o bitwarden.zip \
    && unzip bitwarden.zip && rm -f bitwarden.zip && chmod +x bw && mv bw /usr/local/bin/ \
    && python3.13 -m venv /app/kiwix-python \
    && git clone --depth=1 --branch=master https://github.com/borgbase/borgbase-api-client.git \
    && cd borgbase-api-client/ \
    && /app/kiwix-python/bin/pip3 install . \
    && cd .. \
    && rm -rf borgbase-api-client \
    && /app/kiwix-python/bin/pip3 install --no-cache-dir --upgrade requests==2.34.2 borgmatic==2.1.6 jsonschema==4.26.0 pyrsistent==0.20.0  \
    && curl -sLo /usr/bin/kubectl "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/${ARCH}/kubectl" \
    && chmod +x /usr/bin/kubectl \
    && curl -sLo /usr/bin/kube-dump "https://raw.githubusercontent.com/WoozyMasta/kube-dump/1.1.2/kube-dump" \
    && chmod +x /usr/bin/kube-dump

WORKDIR /root
COPY entrypoint.sh /usr/bin/entrypoint
COPY bin/ /usr/local/bin/
RUN chmod +x /usr/bin/entrypoint \
    && chmod -R 0500 /usr/local/bin/* \
    && mkdir -p .ssh .config/borgmatic/ /config /storage /restore

ENTRYPOINT ["/usr/bin/entrypoint"]
CMD ["backup"]
