FROM python:3.10.13-slim

ENV PYTHONUNBUFFERED=1

COPY ./ /app
WORKDIR /app

RUN apt update
RUN apt install libglib2.0-0 libgl1-mesa-glx -y

RUN pip3 install --upgrade pip setuptools
RUN pip3 install -r requirements.txt
RUN pip3 install .

RUN mkdir -p /app/run/uploads
RUN mkdir -p /app/run/discovery
RUN mkdir -p /app/run/info

RUN cp /app/docker/config.yaml /app/run
RUN cp /app/docker/config.yaml /app/datams

RUN cp /app/docker/gunicorn_entrypoint.sh /app
RUN chmod 770 /app/gunicorn_entrypoint.sh

RUN cp /app/docker/celery_entrypoint.sh /app
RUN chmod 770 /app/celery_entrypoint.sh

RUN rm -r /app/docker
RUN rm /app/docker-compose.yaml

CMD ["gunicorn_entrypoint.sh"]