#!/bin/bash

# Creates Cron Job which backups DB in Docker everyday Friday at midnight host time
command="docker exec postgres /bin/bash -c '/scripts/postgres_dump.sh'"
(crontab -l | grep -v -F "$command" ; echo "0 0 * * FRI ($command) 2>&1 | logger -t PG_DUMP") | crontab
echo "postgres dump task added to host crontab and scheduled to execute every friday at midnight"