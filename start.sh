#!/bin/bash
python manage.py migrate
python manage.py collectstatic --noinput
django-admin compilemessages -l fa
#celery -A core worker -l debug --pool solo -B --detach --logfile /app/celery-logfile.log
gunicorn --bind 0.0.0.0:80 --workers=2 --worker-class=gevent --worker-connections=20  core.wsgi:application
