#!/bin/bash

# flask --app datams run -h 0.0.0.0 -p 8000 --debug
gunicorn --workers ${NUM_GUNICORN_WORKERS} --bind 0.0.0.0:8000 wsgi:app