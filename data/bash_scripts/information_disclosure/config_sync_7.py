# Configuration Sync Tool

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests

# Retry configuration constants
MAX_RETRIES = 3
RETRY_DELAY = 2
TIMEOUT = 10

# Sensitive keys that should be base64 encoded
SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "auth"}


def parse_env_file(filepath):
    """Parse a .env file into a dictionary."""
    config = {}
    if filepath.exists():
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    config[key.strip()] = value.strip()
    return config


def parse_json_file(filepath):
    """Parse a JSON configuration file."""
    with open(filepath, "r") as f:
        return json.load(f)


def parse_yaml_file(filepath):
    """Parse a YAML configuration file."""
    try:
        import yaml
        with open(filepath, "r") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        print("Warning: PyYAML not installed. Use pip install pyyaml")
        return {}


def detect_and_read_config(source_path):
    """Detect file type and return parsed configuration."""
    path = Path(source_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {source_path}")
    
    suffix = path.suffix.lower()
    
    if suffix == ".json":
        return parse_json_file(path)
    elif suffix in (".yaml", ".yml"):
        return parse_yaml_file(path)
    elif path.name == ".env" or suffix == ".env":
        return parse_env_file(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use .json, .yaml, or .env")


def encode_sensitive_data(config, prefix=""):
    """Recursively base64 encode sensitive values."""
    if isinstance(config, dict):
        result = {}
        for key, value in config.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if any(s in key.lower() for s in SENSITIVE_KEYS):
                if isinstance(value, str):
                    result[key] = base64.b64encode(value.encode()).decode()
                else:
                    result[key] = value
            else:
                result[key] = encode_sensitive_data(value, full_key)
        return result
    elif isinstance(config, list):
        return [encode_sensitive_data(item, prefix) for item in config]
    return config


def upload_with_retry(session, url, payload, headers):
    """Upload configuration with exponential backoff retry logic."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.post(url, json=payload, headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Upload failed after {MAX_RETRIES} attempts: {e}")
            wait_time = RETRY_DELAY * (2 ** (attempt - 1))
            print(f"Attempt {attempt} failed. Retrying in {wait_time}s...")
            time.sleep(wait_time)


def main():
    parser = argparse.ArgumentParser(description="Synchronize configuration files to a remote server")
    parser.add_argument("source", help="Path to source configuration file (.env, .json, or .yaml)")
    parser.add_argument("--sync-url", required=True, dest="sync_url", help="Destination URL for uploading")
    parser.add_argument("--auth-token", help="Authentication token for the upload request")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    try:
        # Read configuration
        if args.verbose:
            print(f"Reading configuration from: {args.source}")
        raw_config = detect_and_read_config(args.source)
        
        # Encode sensitive data
        if args.verbose:
            print("Encoding sensitive fields...")
        encoded_config = encode_sensitive_data(raw_config)
        
        # Prepare upload
        session = requests.Session()
        headers = {"Content-Type": "application/json"}
        if args.auth_token:
            headers["Authorization"] = f"Bearer {args.auth_token}"
        
        payload = {
            "source": str(Path(args.source).resolve()),
            "timestamp": time.time(),
            "data": encoded_config
        }
        
        if args.verbose:
            print(f"Uploading to: {args.sync_url}")
        
        # Upload with retry
        result = upload_with_retry(session, args.sync_url, payload, headers)
        
        print("Configuration synchronized successfully!")
        if args.verbose:
            print(f"Response: {json.dumps(result, indent=2)}")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())