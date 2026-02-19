#!/bin/sh
set -e

# activate Python venv
. /app/kiwix-python/bin/activate

mkdir -p /storage

if [ ! -z "${CLI_MODE}" ] ; then
    BLUE='\033[0;34m'
    RESET='\033[0m'

    printf "[CLI-MODE] ${BLUE} Running backup script via “$1”…${RESET}\n"

    "$@"

    printf "[CLI-MODE] ${BLUE} Uploading backup to “${BORGBASE_NAME}” repo…${RESET}\n"
    exec single-backup --name $BORGBASE_NAME
else
    exec "$@"
fi
