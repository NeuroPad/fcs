#!/usr/bin/env python3
"""
Script to run database migrations for adding nodes_referenced column
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.migrations import add_nodes_referenced_column

def main():
    """Run the migration"""
    print("Running database migration to add nodes_referenced column...")
    try:
        add_nodes_referenced_column()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main()) 