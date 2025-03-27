import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Add the apps directory to the Python path
sys.path.insert(0, str(BASE_DIR / "apps"))

# Define path for the environment file
env_path = BASE_DIR.parent / ".env"


def load_environment_files():
    """
    Load environment variables from .env file.

    Simple, straightforward approach for Docker and local environments.
    """
    if env_path.exists():
        print(f"Loading environment file: {env_path}")
        load_dotenv(env_path)
    else:
        print("No .env file found. Using system environment variables.")
