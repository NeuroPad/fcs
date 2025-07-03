FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including build tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml poetry.lock* /app/

# Install Poetry using pip instead of the installer script
RUN pip install poetry==2.1.2 && \
    poetry --version

# Install dependencies with retry mechanism
RUN for i in 1 2 3; do \
        poetry config virtualenvs.create false && \
        poetry install --no-interaction --no-ansi && break || \
        echo "Retry installing dependencies: $i" && \
        sleep 10; \
    done

# Copy the startup script first and set permissions
COPY start.sh /app/
RUN chmod +x /app/start.sh

# Copy the rest of the application
COPY . /app/

# Create models directory
RUN mkdir -p /app/models

# Download BGE model with retry mechanism and existence check
RUN if [ ! -d "/app/models/bge-small-en-v1.5" ]; then \
        for i in 1 2 3; do \
            python -c "from huggingface_hub import snapshot_download; \
            snapshot_download(repo_id='BAAI/bge-small-en-v1.5', local_dir='/app/models/bge-small-en-v1.5', local_dir_use_symlinks=False)" && \
            break || \
            echo "Retry downloading BGE model: $i" && \
            sleep 10; \
        done; \
    else \
        echo "BGE model already exists, skipping download"; \
    fi

# # Download Relik model with retry mechanism and existence check
# RUN if [ ! -d "/app/models/relik-relation-extraction-small" ]; then \
#         for i in 1 2 3; do \
#             python -c "from huggingface_hub import snapshot_download; \
#             snapshot_download(repo_id='relik-ie/relik-relation-extraction-small', local_dir='/app/models/relik-relation-extraction-small', local_dir_use_symlinks=False)" && \
#             break || \
#             echo "Retry downloading Relik model: $i" && \
#             sleep 10; \
#         done; \
#     else \
#         echo "Relik model already exists, skipping download"; \
#     fi

# Install CLIP using Poetry with retry mechanism
# RUN poetry run python -c "import clip" || \
#     for i in 1 2 3; do \
#         poetry add git+https://github.com/openai/CLIP.git && \
#         break || \
#         echo "Retry installing CLIP: $i" && \
#         sleep 10; \
#     done

# Expose the port the app runs on
EXPOSE 8000

# Use shell form to ensure proper shell execution
CMD /bin/bash /app/start.sh