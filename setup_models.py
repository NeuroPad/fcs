#!/usr/bin/env python3
"""
Setup script to download and prepare models for the project.
This replaces the bash script with a more portable Python solution.
Uses Poetry for dependency management.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import json

# Define the models directory
PROJECT_ROOT = Path(__file__).parent.absolute()
MODELS_DIR = PROJECT_ROOT / "models"

def run_command(command, description=None):
    """Run a shell command and print its output"""
    if description:
        print(f"\n{description}...")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    
    print(result.stdout)
    return True

def check_poetry_installed():
    """Check if Poetry is installed"""
    result = subprocess.run("poetry --version", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("Poetry is not installed. Please install it first:")
        print("curl -sSL https://install.python-poetry.org | python3 -")
        return False
    return True

def install_requirements():
    """Install project requirements using Poetry"""
    if not check_poetry_installed():
        return False
    
    # Check if dependencies are already installed
    print("Checking Poetry dependencies...")
    
    # Install dependencies
    return run_command("poetry install", "Installing project dependencies with Poetry")

def setup_spacy():
    """Download and setup spaCy models"""
    # Create models directory if it doesn't exist
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    # Download spaCy model
    print("Setting up spaCy models...")
    
    # Check if model is already downloaded
    spacy_model_path = MODELS_DIR / "en_core_web_lg"
    if spacy_model_path.exists() or spacy_model_path.is_symlink():
        # Remove existing symlink or directory
        if spacy_model_path.is_symlink():
            spacy_model_path.unlink()
        elif spacy_model_path.is_dir():
            shutil.rmtree(spacy_model_path)
        print(f"Removed existing SpaCy model at {spacy_model_path}")
    
    # Download the model using Poetry
    run_command("poetry run python -m spacy download en_core_web_lg")
    
    # Find where spacy downloaded the model
    result = subprocess.run(
        "poetry run python -c \"import spacy; print(spacy.util.get_package_path('en_core_web_lg'))\"",
        shell=True, capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"Error finding spaCy model path: {result.stderr}")
        return False
    
    model_path = Path(result.stdout.strip())
    
    # Create a symlink or copy to our models directory
    if os.name == 'nt':  # Windows
        shutil.copytree(model_path, spacy_model_path)
    else:  # Unix-like
        os.symlink(model_path, spacy_model_path)
    
    print(f"SpaCy model linked to {spacy_model_path}")
    
    return True

def setup_huggingface_models():
    """Download and setup Hugging Face models"""
    print("Setting up Hugging Face models...")
    
    # Check if huggingface_hub is installed
    result = subprocess.run(
        "poetry run python -c \"from huggingface_hub import snapshot_download\"",
        shell=True, capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print("Installing huggingface_hub...")
        run_command("poetry add huggingface_hub")
    
    # BGE model
    bge_model_path = MODELS_DIR / "bge-small-en-v1.5"
    if not bge_model_path.exists():
        print("Downloading BGE embedding model...")
        run_command(
            f"poetry run python -c \"from huggingface_hub import snapshot_download; "
            f"snapshot_download(repo_id='BAAI/bge-small-en-v1.5', local_dir='{bge_model_path}', local_dir_use_symlinks=False)\""
        )
    else:
        print(f"BGE model already exists at {bge_model_path}")
    
    return True

def setup_relik():
    """Download and setup Relik models"""
    print("Setting up Relik models...")
    
    # Check if relik is in pyproject.toml
    # It's already there as a git dependency, so we don't need to add it
    
    # Download Relik model
    relik_model_path = MODELS_DIR / "relik-relation-extraction-small"
    if not relik_model_path.exists():
        print("Downloading Relik model...")
        run_command(
            f"poetry run python -c \"from huggingface_hub import snapshot_download; "
            f"snapshot_download(repo_id='relik-ie/relik-relation-extraction-small', local_dir='{relik_model_path}', local_dir_use_symlinks=False)\""
        )
    else:
        print(f"Relik model already exists at {relik_model_path}")
    
    return True

def setup_clip():
    """Install CLIP and its dependencies"""
    print("Setting up CLIP...")
    
    # Check if CLIP dependencies are in pyproject.toml
    # llama-index-embeddings-clip is already there
    
    # Check if CLIP is installed
    result = subprocess.run(
        "poetry run python -c \"import clip\"",
        shell=True, capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print("Installing CLIP from GitHub...")
        run_command("poetry add git+https://github.com/openai/CLIP.git")
    
    return True

def main():
    """Main function to run all setup steps"""
    print(f"Setting up models in {MODELS_DIR}")
    
    # Create models directory
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    # Run setup steps
    steps = [
        install_requirements,
        setup_spacy,
        setup_huggingface_models,
        setup_relik,
        setup_clip
    ]
    
    for step in steps:
        if not step():
            print(f"Error during {step.__name__}")
            return 1
    
    print("\nSetup completed successfully!")
    print(f"Models are stored in: {MODELS_DIR}")
    print("\nTo use the models in your project, make sure to update your code to load models from:")
    print(f"  {MODELS_DIR}")
    return 0

if __name__ == "__main__":
    sys.exit(main())