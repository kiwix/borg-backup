#!/bin/bash
#
# Author : Florent Kaisser <florent.pro@kaisser.name>
#
# ENV :
# - BORGBASE_NAME : name of backup
# - BW_EMAIL : BitWarden account email used to retrieve the key pair and the BorgBase token
# - BW_PASSWORD : BitWarden master password

SSH_DIR=`pwd`/.ssh
SSH_PRIV_KEY_FILE=${SSH_DIR}/${BORGBASE_NAME}_id
SSH_PUB_KEY_FILE=${SSH_PRIV_KEY_FILE}.pub

CMD=$@

export BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK=yes 
export BORG_RELOCATED_REPO_ACCESS_IS_OK=yes

function create_ssh_config_file {
    export KNOWN_HOSTS_FILE=${SSH_DIR}/known_hosts
    CONFIG_FILE=${SSH_DIR}/config

    echo -e \
    "Host *.borgbase.com\n" \
    "  IdentityFile ${SSH_PRIV_KEY_FILE}\n" \
    "  UserKnownHostsFile ${KNOWN_HOSTS_FILE}" \
    > ${CONFIG_FILE}

    chmod 600 ${CONFIG_FILE}
}

function init_config {
    export BW_SESSION=`bw login --raw ${BW_EMAIL} ${BW_PASSWORD}`

    if bw get username ${BORGBASE_NAME} > ${SSH_PUB_KEY_FILE}
    then
        echo "SSH key retrieval success"
        echo >> ${SSH_PUB_KEY_FILE}
        bw get password ${BORGBASE_NAME} > ${SSH_PRIV_KEY_FILE}
        echo >> ${SSH_PRIV_KEY_FILE}
        chmod 600 ${SSH_PRIV_KEY_FILE}
        BORGBASE_KEY=`bw list items --search test_borg | jq '.[0] | .fields | .[] |  select(.name=="BORGBASE_KEY") | .value  2>/dev/null'`
        export BORGBASE_KEY
    else
        echo "Cannot get BorgBase credentials, please setup the repo."
        exit 1
    fi

    bw logout

    create_ssh_config_file

    chown -R root ${SSH_DIR}
}

function init_cron {
    BORGMATIC_CRON="/etc/cron.hourly/borgmatic"
    BORGMATIC_CONFIG="/root/.config/borgmatic/config.yaml"
    BORGMATIC_CMD="/usr/local/bin/borgmatic -c ${BORGMATIC_CONFIG} --verbosity 1 --files"
    BORGMATIC_LOG_FILE="/dev/shm/borgmatic.log"

    # Save borgmatic config
    cp ${BORGMATIC_CONFIG} /config/borgmatic.yaml

    # Install Cron
    { \
        echo "#!/bin/sh" ; \
        echo "/usr/bin/flock -w 0 /dev/shm/cron.lock ${BORGMATIC_CMD} 2>&1 | tee -a ${BORGMATIC_LOG_FILE} " ; \
    } > ${BORGMATIC_CRON} && chmod 0500 ${BORGMATIC_CRON}

    #Initial backup on start
    echo "@reboot root ${BORGMATIC_CMD} 2>&1 | tee -a ${BORGMATIC_LOG_FILE}" >> /etc/crontab
}

echo "Start initialization ..."

init_config

if ! init_borgbase_repository.py
then
    exit 2
fi

init_cron

echo "Initialization complete, run $CMD"

$CMD
