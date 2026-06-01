# Configuration Sync Tool

import argparse
import base64
import json
import os
import time
import yaml
from pathlib import Path
import requests

# Define constants
DEFAULT_SYNC_URL = "https://api.configsync.io/v1/upload"
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2
SENSITIVE_FIELD_SUFFIX = "_secret"


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Synchronize configuration files to a remote server.")
    parser.add_argument("source", type=str, help="Path to the source configuration file.")
    parser.add_argument("destination", type=str, help="Destination identifier or path.")
    parser.add_argument("--sync-url", type=str, default=DEFAULT_SYNC_URL, help="URL for the sync endpoint.")
    parser.add_argument("--retries", type=int, default=MAX_RETRY_ATTEMPTS, help="Number of retry attempts.")
    parser.add_argument("--delay", type=float, default=RETRY_DELAY_SECONDS, help="Delay between retries in seconds.")
    return parser.parse_args()


def detect_file_type(file_path: str) -> str:
    """Detect the file type based on the extension."""
    path = Path(file_path)
    if path.suffix == ".json":
        return "json"
    elif path.suffix == ".yaml" or path.suffix == ".yml":
        return "yaml"
    elif path.name == ".env" or path.suffix == ".env":
        return "env"
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")


def read_configuration(file_path: str) -> dict:
    """Read and parse the configuration file."""
    try:
        with open(file_path, "r") as f:
            content = f.read()

        file_type = detect_file_type(file_path)

        if file_type == "json":
            return json.loads(content)
        elif file_type == "yaml":
            return yaml.safe_load(content) or {}
        elif file_type == "env":
            config = {}
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
            return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {e}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in configuration file: {e}")


def encode_sensitive_data(config: dict) -> dict:
    """Encode sensitive fields using base64."""
    encoded_config = {}
    for key, value in config.items():
        if isinstance(value, str) and key.endswith(SENSITIVE_FIELD_SUFFIX):
            encoded_config[key] = base64.b64encode(value.encode("utf-8")).decode("utf-8")
        else:
            encoded_config[key] = value
    return encoded_config


def upload_configuration(config_data: dict, sync_url: str, retries: int, delay: float) -> bool:
    """Upload configuration to the remote server with retry logic."""
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ConfigSync-Client/1.0"
    }

    payload = json.dumps({
        "config": config_data,
        "timestamp": time.time()
    })

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(sync_url, data=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                print(f"Successfully uploaded configuration (Attempt {attempt})")
                return True
            else:
                print(f"Upload failed with status {response.status_code} (Attempt {attempt}/{retries})")
        except requests.exceptions.RequestException as e:
            print(f"Request error on attempt {attempt}: {e}")

        if attempt < retries:
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)

    return False


def main():
    """Main entry point for the configuration sync tool."""
    args = parse_arguments()

    try:
        config = read_configuration(args.source)
        config = encode_sensitive_data(config)
        
        success = upload_configuration(config, args.sync_url, args.retries, args.delay)
        
        if success:
            print("Configuration synchronization completed successfully.")
        else:
            print("Configuration synchronization failed after all retries.")
            exit(1)

    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()