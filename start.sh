#!/bin/bash

# Wait for a few seconds to ensure other services are up
sleep 5

# Run database setup
python /app/setup_db.py

# Run migrations
python -m alembic upgrade head

# Start the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop asyncio 