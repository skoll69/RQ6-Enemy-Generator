# Mythras Encounter Generator

A tool for Mythras GM's for generating enemy stats.

Hosted at https://mythras.skoll.xyz/

## Dev env installation

Mythras Encounter Generator has been tested with Python 3.8.10. Other versions might or might not work.

* Copy `mythras_eg/settings_example.py` to `mythras_eg/settings.py`
* In `settings.py`
  * Fill in DB configuration
  * Update `PROJECT_ROOT` to point to you source directory
* It is recommended to create a virtualenv
* Install requirements from `requirements.txt`
* Unzip `dump.zip` and import it to your local database
* Create a folder named `temp` in the project directory (it's not possible to add empty folders to git)

### WeasyPrint

If you want to use PDF/PNG export features, follow OS-specific installation instructions for WeasyPrint at
https://weasyprint.readthedocs.io/en/stable/install.html

## Start Dev env

### Windows

`python.exe .\manage.py runserver`
