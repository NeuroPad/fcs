FROM python:3.11-slim

# Fix package installation issues and install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Add Cargo to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

# Set pip timeout and retries
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_RETRIES=10

# Install Poetry with increased timeout
RUN pip install --timeout 300 poetry==1.8.4

# Set working directory
WORKDIR /app

# Copy only dependencies first
COPY pyproject.toml poetry.lock ./

# Install Python dependencies with retry mechanism
RUN poetry config virtualenvs.create false && \
    for i in $(seq 1 3); do \
        poetry install --no-interaction --no-ansi && break || \
        if [ $i -lt 3 ]; then \
            echo "Retry $i of 3..." && \
            sleep 5; \
        else \
            exit 1; \
        fi \
    done

# Copy application
COPY . .

# Run command with --loop=asyncio
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "asyncio"]