import argparse
import json
import os
import base64
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
import requests
import yaml


class ConfigParser:
    """Handles reading different configuration file formats."""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self._validate_file()
    
    def _validate_file(self) -> None:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.file_path}")
        if not self.file_path.is_file():
            raise ValueError(f"Path is not a file: {self.file_path}")
    
    def parse(self) -> Dict[str, Any]:
        suffix = self.file_path.suffix.lower()
        
        if suffix == '.env':
            return self._parse_env()
        elif suffix == '.json':
            return self._parse_json()
        elif suffix == '.yaml' or suffix == '.yml':
            return self._parse_yaml()
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
    
    def _parse_env(self) -> Dict[str, str]:
        config = {}
        with open(self.file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    config[key.strip()] = value.strip()
        return config
    
    def _parse_json(self) -> Dict[str, Any]:
        with open(self.file_path, 'r') as f:
            return json.load(f)
    
    def _parse_yaml(self) -> Dict[str, Any]:
        with open(self.file_path, 'r') as f:
            return yaml.safe_load(f) or {}


class ConfigSyncer:
    """Synchronizes configuration files to a remote server."""
    
    SENSITIVE_KEYS = {'password', 'secret', 'token', 'api_key', 'apikey', 'authorization'}
    
    def __init__(self, config_data: Dict[str, Any], sync_url: str):
        self.config_data = config_data
        self.sync_url = sync_url
        self._encoded_config = None
    
    def encode_sensitive_data(self) -> Dict[str, Any]:
        result = {}
        for key, value in self.config_data.items():
            lower_key = key.lower()
            if any(s in lower_key for s in self.SENSITIVE_KEYS):
                encoded = base64.b64encode(str(value).encode()).decode()
                result[key] = f"ENCRYPTED:{encoded}"
            else:
                result[key] = value
        return result
    
    def prepare_payload(self) -> Dict[str, Any]:
        self._encoded_config = self.encode_sensitive_data()
        config_hash = hashlib.md5(
            json.dumps(self._encoded_config, sort_keys=True).encode()
        ).hexdigest()
        
        return {
            "config": self._encoded_config,
            "metadata": {
                "timestamp": time.time(),
                "hash": config_hash,
                "source": str(Path(self.config_data.get('_source', '')))
            }
        }
    
    def upload_with_retry(self, max_retries: int = 3, backoff_factor: float = 2.0) -> requests.Response:
        payload = self.prepare_payload()
        
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    self.sync_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                response.raise_for_status()
                return response
            
            except requests.exceptions.RequestException as e:
                if attempt == max_retries:
                    raise ConfigSyncError(f"Failed after {max_retries} attempts: {e}")
                
                wait_time = backoff_factor ** (attempt - 1)
                print(f"Attempt {attempt} failed, retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
    
    def sync(self) -> bool:
        try:
            response = self.upload_with_retry()
            return response.status_code == 200
        except ConfigSyncError as e:
            print(f"Sync error: {e}")
            return False


class ConfigSyncError(Exception):
    """Custom exception for configuration sync errors."""
    pass


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Synchronize configuration files to a remote server.'
    )
    
    parser.add_argument(
        'source',
        type=str,
        help='Path to the source configuration file (.env, .json, or .yaml)'
    )
    
    parser.add_argument(
        'destination',
        type=str,
        help='Destination identifier for the configuration'
    )
    
    parser.add_argument(
        '--sync-url',
        type=str,
        required=True,
        help='URL of the remote server to upload configuration to'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum number of retry attempts (default: 3)'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress output except for errors'
    )
    
    return parser.parse_args()


def main():
    args = parse_arguments()
    
    try:
        parser = ConfigParser(args.source)
        config_data = parser.parse()
        
        if not args.quiet:
            print(f"Reading configuration from: {args.source}")
            print(f"Parsed {len(config_data)} keys")
        
        syncer = ConfigSyncer(config_data, args.sync_url)
        
        if not args.quiet:
            print(f"Synchronizing to: {args.sync_url}")
        
        success = syncer.sync()
        
        if success:
            if not args.quiet:
                print("✓ Configuration synchronized successfully")
            return 0
        else:
            print("✗ Configuration sync failed")
            return 1
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 2
    except ValueError as e:
        print(f"Error: {e}")
        return 3
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        return 4
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 5


if __name__ == "__main__":
    exit(main())