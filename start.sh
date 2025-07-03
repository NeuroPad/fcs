#!/bin/bash

# Wait for a few seconds to ensure other services are up
sleep 5

# Run database setup
python setup_db.py

# Run migrations
alembic upgrade head

# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop asyncio 