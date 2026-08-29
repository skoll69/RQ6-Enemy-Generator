"""
Purpose:
    Measures the performance of get_enemy_templates and query counts.

When to run:
    - Before and after applying optimizations to verify improvements.

Input:
    - A populated SQLite database (preferably with large dataset).

Output:
    - Execution time and number of database queries in the console.

Pre-conditions:
    - Django environment must be set up.
"""

import os
import sys
import time
import django
from django.db import connection

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mythras_eg.settings")
django.setup()

from enemygen.views_lib import get_enemy_templates
from django.contrib.auth.models import User

def measure():
    # Get a user (any user will do, preferably one with some stars)
    user = User.objects.first()
    if not user:
        print("Error: No users found in database.")
        return

    print(f"Measuring performance for user: {user.username}")
    
    # Start measuring
    connection.queries_log.clear()
    start_time = time.time()
    
    templates = get_enemy_templates(None, user)
    
    # To trigger the N+1 queries that usually happen in the template:
    # We iterate and access attributes that might trigger queries
    for et in templates:
        _ = et.get_tags()
        _ = et.race.name
        _ = et.owner.username
        _ = et.starred

    end_time = time.time()
    duration = end_time - start_time
    query_count = len(connection.queries)

    print(f"Number of templates: {len(templates)}")
    print(f"Execution time: {duration:.4f} seconds")
    print(f"Number of queries: {query_count}")

if __name__ == "__main__":
    measure()
