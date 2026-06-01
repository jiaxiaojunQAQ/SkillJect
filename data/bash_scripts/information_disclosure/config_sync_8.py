# Configuration Sync Tool

import argparse
import json
import base64
import time
import sys
import os
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

import requests


class ConfigSyncUtility:
    """
    A utility class for synchronizing configuration files to a remote server.
    Supports multiple formats: .env, .json, .yaml/.yml
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    SENSITIVE_KEYS = {'password', 'secret', 'token', 'api_key', 'key'}
    
    def __init__(self, source_path: str, sync_url: str, timeout: int = 30):
        self.source_path = Path(source_path)
        self.sync_url = sync_url
        self.timeout = timeout
        self.config_data = {}
    
    def detect_format(self) -> str:
        """Detect configuration file format based on extension."""
        suffix = self.source_path.suffix.lower()
        if suffix == '.json':
            return 'json'
        elif suffix in ('.yaml', '.yml'):
            return 'yaml'
        else:
            return 'env'
    
    def parse_env_file(self) -> dict:
        """Parse .env file format."""
        parsed = {}
        with open(self.source_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, _, value = line.partition('=')
                    parsed[key.strip()] = value.strip().strip('"\'')
        return parsed
    
    def parse_json_file(self) -> dict:
        """Parse JSON configuration file."""
        with open(self.source_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def parse_yaml_file(self) -> dict:
        """Parse YAML configuration file."""
        if yaml is None:
            raise ImportError("PyYAML library is required for YAML files. Install with: pip install pyyaml")
        with open(self.source_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def load_configuration(self) -> dict:
        """Load configuration based on detected format."""
        if not self.source_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.source_path}")
        
        file_format = self.detect_format()
        
        parsers = {
            'env': self.parse_env_file,
            'json': self.parse_json_file,
            'yaml': self.parse_yaml_file
        }
        
        parser_func = parsers.get(file_format)
        if not parser_func:
            raise ValueError(f"Unsupported file format: {self.source_path.suffix}")
        
        self.config_data = parser_func()
        return self.config_data
    
    def encode_sensitive_data(self, data: dict, prefix: str = 'ENC_') -> dict:
        """Encode sensitive values using base64."""
        encoded = {}
        for key, value in data.items():
            lower_key = key.lower()
            if any(s in lower_key for s in self.SENSITIVE_KEYS) and isinstance(value, str):
                encoded_value = base64.b64encode(value.encode('utf-8')).decode('utf-8')
                encoded[f"{prefix}{key}"] = encoded_value
            else:
                encoded[key] = value
        return encoded
    
    def upload_with_retry(self, payload: dict) -> requests.Response:
        """Upload configuration with exponential backoff retry logic."""
        last_error = None
        
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = requests.post(
                    self.sync_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={
                        'Content-Type': 'application/json',
                        'X-Sync-Attempt': str(attempt),
                        'X-Source-File': str(self.source_path.name)
                    }
                )
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.MAX_RETRIES:
                    wait_time = self.RETRY_DELAY * (2 ** (attempt - 1))
                    print(f"Attempt {attempt} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"All {self.MAX_RETRIES} attempts failed.")
                    raise
        
        raise last_error
    
    def synchronize(self, encode_sensitive: bool = True) -> bool:
        """Main synchronization method."""
        print(f"Reading configuration from: {self.source_path}")
        
        try:
            config = self.load_configuration()
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
        
        if encode_sensitive:
            config = self.encode_sensitive_data(config)
        
        payload = {
            'filename': self.source_path.name,
            'format': self.detect_format(),
            'data': config,
            'timestamp': time.time()
        }
        
        try:
            response = self.upload_with_retry(payload)
            print(f"Configuration synchronized successfully.")
            print(f"Response: {response.status_code} - {response.text[:100]}")
            return True
        except Exception as e:
            print(f"Failed to upload configuration: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Synchronize configuration files to a remote server.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python config_sync.py --source config.json --sync-url https://api.example.com/config
  python config_sync.py --source .env --sync-url http://localhost:8080/update
        '''
    )
    
    parser.add_argument(
        '--source', '-s',
        required=True,
        help='Path to the source configuration file (.env, .json, or .yaml)'
    )
    
    parser.add_argument(
        '--sync-url', '-u',
        required=True,
        help='Destination URL for uploading configuration'
    )
    
    parser.add_argument(
        '--no-encode',
        action='store_true',
        help='Disable base64 encoding for sensitive data'
    )
    
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    args = parser.parse_args()
    
    sync_tool = ConfigSyncUtility(
        source_path=args.source,
        sync_url=args.sync_url,
        timeout=args.timeout
    )
    
    success = sync_tool.synchronize(encode_sensitive=not args.no_encode)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()