FROM postgres:15-alpine3.18

RUN mkdir -p /scripts
RUN mkdir -p /docker-entrypoint-initdb.d
COPY docker/postgres_dump.sh /scripts
RUN chmod 770 /scripts/postgres_dump.sh