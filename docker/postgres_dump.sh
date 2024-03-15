#!/bin/bash

mkdir -p /var/lib/postgresql/data/dumps
now=$(date +"%Y-%m-%d_%H%M%S")
pg_dump -U $POSTGRES_USER $POSTGRES_DB > "/var/lib/postgresql/data/dumps/datams_dump_$now.sql"

# remove all files (type f) modified longer than 365 days ago under /db_backups/backups
find /var/lib/postgresql/data/dumps/ -name "*.sql" -type f -mtime +365 -delete