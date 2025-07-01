#!/usr/bin/env python3
"""
Database setup script for MemDuo.

This script handles:
1. Running Alembic migrations
2. Initializing the database with default data
3. Creating an admin user
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.db.init_db import main as init_db_main
from app.core.logging import setup_logging

logger = setup_logging()


def run_migrations():
    """Run Alembic migrations."""
    import subprocess
    
    logger.info("Running database migrations...")
    try:
        result = subprocess.run(
            ["poetry", "run", "alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("✅ Migrations completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Migration failed: {e}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        return False


def main():
    """Main setup function."""
    logger.info("🚀 Starting database setup...")
    
    # Run migrations
    if not run_migrations():
        logger.error("❌ Database setup failed at migration step")
        sys.exit(1)
    
    # Initialize database with default data
    logger.info("Initializing database with default data...")
    try:
        init_db_main()
        logger.info("✅ Database setup completed successfully!")
        logger.info("📝 Default admin user: admin@memduo.com / admin123")
        logger.info("⚠️  Please change the admin password in production!")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 