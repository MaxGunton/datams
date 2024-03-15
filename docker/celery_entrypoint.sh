#!/bin/bash

celery --app make_celery worker --loglevel=INFO && celery --app make_celery beat