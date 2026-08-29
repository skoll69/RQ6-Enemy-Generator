"""
Purpose:
    Imports custom features, names, or items from a text file into AdditionalFeatureLists.

When to run:
    - When adding new content packs or research-based lists to the encounter generator.

Why to run:
    - Allows for rapid population of random generation tables from simple text files.
    - Handles the creation of the parent 'AdditionalFeatureList' automatically.

Input:
    - A plain text file (one item per line). Default: 'medieval german male'.
    - Configuration in `main()` for list name and type.

Output:
    - Database entries in 'enemygen_additionalfeaturelist' and 'enemygen_additionalfeatureitem'.

End result:
    - New content is available in the application's generation logic (e.g., as a new random name list).

Pre-conditions:
    - The 'db.sqlite3' database must exist and be migrated.

Developer info:
    - Supports three list types: 'name', 'enemy_feature', and 'party_feature'.
    - Uses `get_or_create` to ensure idempotency.
"""
import os
import sys
import django
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add project root to sys.path to allow importing mythras_eg.settings and enemygen
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mythras_eg.settings")
django.setup()

from enemygen.models import AdditionalFeatureList, AdditionalFeatureItem

class FeatureImporter:
    """Imports features or names from a text file into AdditionalFeatureList."""

    def __init__(self, file_path: str, list_name: str, list_type: str):
        """
        Initialize the importer.

        Args:
            file_path: Path to the text file containing features/names.
            list_name: The name of the AdditionalFeatureList to add to.
            list_type: The type of the list ('name', 'enemy_feature', 'party_feature').
        """
        self.file_path = file_path
        self.list_name = list_name
        self.list_type = list_type

    def run(self) -> None:
        """
        Execute the import process.

        Reads the text file line by line and creates AdditionalFeatureItem
        records associated with the specified list.
        """
        if not os.path.exists(self.file_path):
            logger.error(f"File not found: {self.file_path}")
            return

        flist, created = AdditionalFeatureList.objects.get_or_create(
            name=self.list_name, 
            type=self.list_type
        )
        if created:
            logger.info(f"Created new AdditionalFeatureList: '{self.list_name}' ({self.list_type})")
            
        processed_count = 0
        imported_count = 0
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for row in f:
                processed_count += 1
                name = row.strip()
                if not name:
                    continue
                    
                try:
                    _, item_created = AdditionalFeatureItem.objects.get_or_create(
                        name=name, 
                        feature_list=flist
                    )
                    if item_created:
                        imported_count += 1
                except Exception as e:
                    logger.exception(f"Error importing row '{name}': {e}")
                    raise
            
        logger.info(f"Summary for '{self.list_name}':")
        logger.info(f"  Processed: {processed_count} lines")
        logger.info(f"  Imported:  {imported_count} new items")

def main() -> None:
    """Main entry point for the feature import script."""
    # Configuration - can be modified as needed
    config = {
        'file_path': 'medieval german male',
        'list_name': 'Medieval German Male',
        'list_type': 'name'  # Options: 'name', 'enemy_feature', 'party_feature'
    }
    
    importer = FeatureImporter(
        config['file_path'], 
        config['list_name'], 
        config['list_type']
    )
    importer.run()

if __name__ == '__main__':
    main()
