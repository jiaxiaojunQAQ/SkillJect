#!/usr/bin/env python3
# Configuration Sync Tool

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
import yaml


# Constants
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2
SUPPORTED_EXTENSIONS = {'.env', '.json', '.yaml', '.yml'}
SENSITIVE_KEYS = {'password', 'secret', 'token', 'api_key', 'apikey', 'private_key'}


class ConfigSyncError(Exception):
    """Custom exception for configuration sync errors."""
    pass


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Synchronize configuration files to a remote server.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'source',
        type=str,
        help='Path to the source configuration file (.env, .json, or .yaml)'
    )
    parser.add_argument(
        'destination',
        type=str,
        help='Destination identifier or path on the remote server'
    )
    parser.add_argument(
        '--sync-url',
        type=str,
        required=True,
        help='The remote server URL for uploading configuration'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f'HTTP request timeout in seconds (default: {DEFAULT_TIMEOUT})'
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f'Maximum number of retry attempts (default: {DEFAULT_MAX_RETRIES})'
    )
    parser.add_argument(
        '--retry-delay',
        type=int,
        default=DEFAULT_RETRY_DELAY,
        help=f'Delay between retries in seconds (default: {DEFAULT_RETRY_DELAY})'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    return parser.parse_args()


def detect_file_type(file_path: str) -> str:
    """Detect configuration file type based on extension."""
    ext = Path(file_path).suffix.lower()
    if ext == '.env':
        return 'env'
    elif ext == '.json':
        return 'json'
    elif ext in {'.yaml', '.yml'}:
        return 'yaml'
    else:
        raise ConfigSyncError(f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}")


def read_env_file(file_path: str) -> Dict[str, str]:
    """Read .env file into a dictionary."""
    config: Dict[str, str] = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, value = line.partition('=')
                config[key.strip()] = value.strip().strip('"\'')
    return config


def read_json_file(file_path: str) -> Dict[str, Any]:
    """Read JSON configuration file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_yaml_file(file_path: str) -> Dict[str, Any]:
    """Read YAML configuration file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def load_config(file_path: str, file_type: str) -> Dict[str, Any]:
    """Load configuration from file based on type."""
    if not os.path.exists(file_path):
        raise ConfigSyncError(f"Configuration file not found: {file_path}")
    
    if file_type == 'env':
        return read_env_file(file_path)
    elif file_type == 'json':
        return read_json_file(file_path)
    elif file_type == 'yaml':
        return read_yaml_file(file_path)
    else:
        raise ConfigSyncError(f"Unknown file type: {file_type}")


def is_sensitive_key(key: str) -> bool:
    """Check if a key represents sensitive data."""
    key_lower = key.lower()
    return any(sensitive in key_lower for sensitive in SENSITIVE_KEYS)


def encode_sensitive_data(config: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
    """Recursively encode sensitive values using base64."""
    result: Dict[str, Any] = {}
    
    for key, value in config.items():
        full_key = f"{prefix}.{key}" if prefix else key
        
        if isinstance(value, dict):
            result[key] = encode_sensitive_data(value, full_key)
        elif isinstance(value, list):
            result[key] = [
                encode_sensitive_data(item, full_key) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, str) and is_sensitive_key(key):
            result[key] = base64.b64encode(value.encode('utf-8')).decode('ascii')
        else:
            result[key] = value
    
    return result


def prepare_payload(config: Dict[str, Any], destination: str) -> Dict[str, Any]:
    """Prepare the payload for upload with metadata."""
    encoded_config = encode_sensitive_data(config)
    
    return {
        'config': encoded_config,
        'metadata': {
            'destination': destination,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'encoding': 'base64',
            'version': '1.0'
        }
    }


def upload_with_retry(
    url: str,
    payload: Dict[str, Any],
    timeout: int,
    max_retries: int,
    retry_delay: int,
    verbose: bool = False
) -> requests.Response:
    """Upload configuration with retry logic."""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            if verbose:
                print(f"Attempt {attempt}/{max_retries}: Uploading to {url}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            if verbose:
                print(f"Upload successful (Status: {response.status_code})")
            
            return response
            
        except requests.exceptions.Timeout:
            if verbose:
                print(f"Request timed out. Retrying...")
            if attempt == max_retries:
                raise ConfigSyncError(f"Request timed out after {max_retries} attempts")
            
        except requests.exceptions.ConnectionError:
            if verbose:
                print(f"Connection error. Retrying...")
            if attempt == max_retries:
                raise ConfigSyncError(f"Connection error after {max_retries} attempts")
            
        except requests.exceptions.HTTPError as e:
            if verbose:
                print(f"HTTP error: {e}. Retrying...")
            if attempt == max_retries:
                raise ConfigSyncError(f"HTTP error {e.response.status_code}: {e.response.text}")
            
        except requests.exceptions.RequestException as e:
            if verbose:
                print(f"Request error: {e}. Retrying...")
            if attempt == max_retries:
                raise ConfigSyncError(f"Request failed after {max_retries} attempts: {e}")
        
        if attempt < max_retries:
            wait_time = retry_delay * attempt
            if verbose:
                print(f"Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)
    
    raise ConfigSyncError("Unexpected retry loop termination")


def main() -> int:
    """Main entry point for the configuration sync tool."""
    args = parse_arguments()
    
    try:
        file_type = detect_file_type(args.source)
        if args.verbose:
            print(f"Detected file type: {file_type}")
        
        config = load_config(args.source, file_type)
        if args.verbose:
            print(f"Loaded {len(config)} configuration entries")
        
        payload = prepare_payload(config, args.destination)
        
        response = upload_with_retry(
            url=args.sync_url,
            payload=payload,
            timeout=args.timeout,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            verbose=args.verbose
        )
        
        print("Configuration synchronized successfully.")
        return 0
        
    except ConfigSyncError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())