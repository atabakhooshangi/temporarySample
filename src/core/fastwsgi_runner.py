"""
WSGI config for core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""
from os.path import abspath, join, dirname
from django.core.wsgi import get_wsgi_application
import os
import sys
import site
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = BASE_DIR
if path not in sys.path:
    sys.path.append(path)
PROJECT_PATH=abspath(join(dirname(__file__), "."))
sys.path.append(PROJECT_PATH)
# Calculate path to site-packages directory.
vepath = PROJECT_PATH+'/env'
python_version = '.'.join(map(str, sys.version_info[:2]))
site_packages = vepath + '/lib/python%s/site-packages' % python_version
# Add the site-packages of the chosen virtualenv to work with
site.addsitedir(vepath)
site.addsitedir(site_packages)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Dev')
application = get_wsgi_application()


# a prototype of a fast WSGI runner
# NOTE: DO NOT RUN IT ON PRODUCTION!!!