#!/bin/bash

# Mythras Encounter Generator - SQLite Setup Script
#
# Purpose:
#   Automates the environment setup for local development using SQLite instead of MySQL.
#
# When to run:
#   - During initial project setup on a new developer machine.
#   - When you need to reset your local database and environment to a clean state.
#
# Why to run:
#   - To quickly get a working Django environment without the overhead of setting up a MySQL server.
#   - Ensures all developers have a consistent local baseline.
#
# Input:
#   - requirements.txt (Python dependencies)
#   - enemygen_testdata.json (Default small test fixture)
#
# Output:
#   - temp/ directory (for generated PDFs/files)
#   - mythras_eg/settings.py (Local Django configuration, if not present)
#   - db.sqlite3 (Initialized SQLite database)
#
# End result:
#   A fully functional local development environment reachable at 127.0.0.1:8000.
#
# Pre-conditions:
#   - Python 3 and pip installed.
#   - Internet access to install dependencies.
#
# Developer info:
#   - This script creates a 'dev' version of settings.py if one doesn't exist.
#   - It defaults to the small 'enemygen_testdata.json' fixture (approx. 2000 objects).
#   - To use production data, follow the migration steps in SQLITE_DEV.md.
#
# Usage:
#   chmod +x dev_tools/setup_sqlite.sh
#   ./dev_tools/setup_sqlite.sh

set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Go to the project root (one level up from dev_tools)
cd "$SCRIPT_DIR/.."

echo "-------------------------------------------------------"
echo "Initializing Mythras Encounter Generator (SQLite Dev)"
echo "-------------------------------------------------------"

# 1. Create 'temp' directory (required by the app)
if [ ! -d "temp" ]; then
    echo "[1/4] Creating 'temp' directory..."
    mkdir temp
else
    echo "[1/4] 'temp' directory already exists."
fi

# 2. Install Dependencies
echo "[2/4] Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# 3. Configure settings.py (if it doesn't exist)
if [ ! -f "mythras_eg/settings.py" ]; then
    echo "[3/4] Creating mythras_eg/settings.py for SQLite..."
    cat <<EOF > mythras_eg/settings.py
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve(strict=True).parent.parent
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100000

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_ROOT, 'db.sqlite3'),
    }
}

SECRET_KEY = 'dev_secret_key'
DEBUG = True
ALLOWED_HOSTS = ['localdev', '127.0.0.1']
ADMINS = ( ('Erkki Lepre', 'erkki.lepre@iki.fi'), )

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'enemygen',
    'django_registration',
    'taggit',
    'django_extensions',
)

MIDDLEWARE = (
    'mythras_eg.middleware.SimpleCorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'mythras_eg.urls'
DEFAULT_AUTO_FIELD='django.db.models.AutoField' 

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(PROJECT_ROOT, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mythras_eg.wsgi.application'
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Helsinki'
USE_I18N = True
USE_L10N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = ( 'static', 'temp' )
ACCOUNT_ACTIVATION_DAYS = 7
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/login/'
TEMP = os.path.join(PROJECT_ROOT, 'temp')
EOF
else
    echo "[3/4] mythras_eg/settings.py already exists."
fi

# 4. Initialize Database
echo "[4/4] Initializing database (migrate & loaddata)..."
python3 manage.py migrate
python3 manage.py loaddata enemygen_testdata.json

echo "-------------------------------------------------------"
echo "Setup Complete!"
echo "Run the server with: python3 manage.py runserver"
echo "Run tests with:      python3 manage.py test"
echo "-------------------------------------------------------"
