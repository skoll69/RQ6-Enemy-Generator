# Mythras Encounter Generator

A tool for Mythras GM's for generating enemy stats.

Hosted at https://mythras.skoll.xyz/

## Dev env installation

Mythras Encounter Generator has been tested with Python 3.11. Other versions might or might not work.

* Copy `mythras_eg/settings_example.py` to `mythras_eg/settings.py`
  * Fill in DB configuration
* It is recommended to create a virtualenv
* Install requirements from `requirements.txt`
* Create a folder named `temp` in the project directory (it's not possible to add empty folders to git)

### WeasyPrint

If you want to use PDF/PNG export features, follow OS-specific installation instructions for WeasyPrint at
https://doc.courtbouillon.org/weasyprint/stable/

## Start Dev env

### Windows

`python.exe .\manage.py runserver`

## AWS Setup reminder list

* Add IPv6 to the VPC
* Create a subnet with IPv6 and Private IPv4
* Add IPv6 to Routing table - Internet Gateway (not Egress Only)
* Create EC2 instance
  * Disable public IPv4 address
* Connect using EC2 Connect Endpoint
* Run script `setup.sh`
