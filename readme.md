# Mythras Encounter Generator

A tool for Mythras GM's for generating enemy stats.

Hosted at https://mythras.skoll.xyz/

## Dev env installation

Mythras Encounter Generator has been tested with Python 3.11. Other versions might or might not work.

### MySQL (Default)
The application is configured to use MySQL by default. 

* Copy `mythras_eg/settings_example.py` to `mythras_eg/settings.py`
  * Fill in DB configuration
* It is recommended to create a virtualenv
* Install requirements from `requirements.txt`
* Create a folder named `temp` in the project directory (it's not possible to add empty folders to git)

### SQLite (Development Alternative)
For a quick local setup using SQLite (recommended for development), you can use the automated script. This will initialize a database with the small default fixture (`enemygen_testdata.json`).

```bash
chmod +x dev_tools/setup_sqlite.sh
./dev_tools/setup_sqlite.sh
```

See [dev_tools/SQLITE_DEV.md](dev_tools/SQLITE_DEV.md) for more details, including how to import a full production MySQL dump into SQLite.

### WeasyPrint

If you want to use PDF/PNG export features, follow OS-specific installation instructions for WeasyPrint at
https://doc.courtbouillon.org/weasyprint/stable/

## Start Dev env

`python manage.py runserver`

## Unit tests

`python manage.py test`

## AWS Setup reminder list

* Add IPv6 to the VPC
* Create a subnet with IPv6 and Private IPv4
* Add IPv6 to Routing table - Internet Gateway (not Egress Only)
* Create EC2 instance
  * Disable public IPv4 address
* Connect using EC2 Connect Endpoint
* Run script `setup.sh`
