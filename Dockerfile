FROM debian:buster-slim
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
# Retry paramaeters when setup a new repo
ENV MAX_BORGMATIC_RETRY="10"
ENV WAIT_BEFORE_BORGMATIC_RETRY="5"

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl jq borgbackup vim python3 python3-pip python3-setuptools openssh-client unzip git cron default-mysql-client postgresql-client && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

RUN curl -Ls 'https://vault.bitwarden.com/download/?app=cli&platform=linux' -o bitwarden.zip && \
    unzip bitwarden.zip && rm -f bitwarden.zip && chmod +x bw && mv bw /usr/local/bin/

RUN git clone --depth=1 --branch=master https://github.com/borgbase/borgbase-api-client.git && \
    mv borgbase-api-client/borgbase_api_client/ /usr/lib/python3/dist-packages/ && \
    rm -rf borgbase-api-client && \
    pip3 install requests

RUN pip3 install --upgrade borgmatic

# Install start script
COPY bin/ /usr/local/bin/
RUN chmod -R 0500 /usr/local/bin/*

WORKDIR /root

RUN mkdir -p .ssh .config/borgmatic/ /config /storage /restore

#ENTRYPOINT ["entrypoint.sh"]

CMD ["backup"]
