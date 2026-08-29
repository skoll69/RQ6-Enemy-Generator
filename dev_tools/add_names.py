"""
Purpose:
    Imports a list of names from a text file into a Django AdditionalFeatureList.

When to run:
    - When you have a bulk list of names (e.g., historical names, fantasy names) to add to the application's generator pool.

Why to run:
    - Manual entry through the Django admin interface is inefficient for large datasets.
    - Automates the association of names with a specific list category.

Input:
    - A plain text file (one name per line). Default: 'orlanthi_males.txt'.

Output:
    - Database entries in the 'enemygen_additionalfeatureitem' table.

End result:
    - The targeted 'AdditionalFeatureList' is populated with new names, making them available during enemy generation.

Pre-conditions:
    - The 'db.sqlite3' database must exist and be migrated.
    - The target 'AdditionalFeatureList' (e.g., 'Orlanthi males') must already exist in the database.

Developer info:
    - This script uses `django.setup()` to access models outside the standard web request cycle.
    - It uses `get_or_create` to avoid duplicating names if the script is run multiple times.
"""
import os
import sys
import django
import logging
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mythras_eg.settings")
django.setup()

from enemygen.models import AdditionalFeatureList, AdditionalFeatureItem

class NameImporter:
    """Handles importing names into the AdditionalFeatureList."""

    def __init__(self, list_name: str, file_path: str):
        """
        Initialize the importer.

        Args:
            list_name: The name of the AdditionalFeatureList to add names to.
            file_path: Path to the text file containing names.
        """
        self.list_name = list_name
        self.file_path = file_path

    def run(self) -> None:
        """
        Execute the import process.

        Raises:
            FileNotFoundError: If the names file does not exist.
            AdditionalFeatureList.DoesNotExist: If the specified list name is not found.
        """
        if not os.path.exists(self.file_path):
            logger.error(f"File not found: {self.file_path}")
            return

        try:
            namelist = AdditionalFeatureList.objects.get(name=self.list_name)
        except AdditionalFeatureList.DoesNotExist:
            logger.error(f"AdditionalFeatureList '{self.list_name}' not found.")
            return

        with open(self.file_path, 'r', encoding='utf-8') as f:
            names = f.read().splitlines()

        count = 0
        for name in names:
            name = name.strip()
            if not name:
                continue
                
            item, created = AdditionalFeatureItem.objects.get_or_create(
                name=name, 
                feature_list=namelist
            )
            if created:
                count += 1
        
        logger.info(f"Successfully imported {count} new names to '{self.list_name}'.")

def main() -> None:
    """Main entry point for the name import script."""
    # Note: These values can be parameterized or moved to a config if needed
    name_list_name = 'Orlanthi males'
    names_file = 'orlanthi_males.txt'
    
    importer = NameImporter(name_list_name, names_file)
    importer.run()

if __name__ == '__main__':
    main()

