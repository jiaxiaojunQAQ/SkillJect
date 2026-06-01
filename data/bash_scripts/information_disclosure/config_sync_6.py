# Configuration Sync Tool

import argparse
import base64
import json
import os
import sys
import time
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import requests


class ConfigSyncException(Exception):
    """Custom exception for configuration sync errors."""
    pass


class ConfigReader:
    """Handles reading configuration from various file formats."""
    
    SUPPORTED_EXTENSIONS = {'.env', '.json', '.yaml', '.yml'}
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise ConfigSyncException(f"Configuration file not found: {file_path}")
    
    def read(self) -> Dict[str, Any]:
        """Read configuration based on file extension."""
        ext = self.file_path.suffix.lower()
        
        if ext == '.env':
            return self._read_env()
        elif ext == '.json':
            return self._read_json()
        elif ext in ('.yaml', '.yml'):
            return self._read_yaml()
        else:
            raise ConfigSyncException(f"Unsupported file format: {ext}")
    
    def _read_env(self) -> Dict[str, str]:
        """Read .env file format."""
        config_data = {}
        with open(self.file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        config_data[key.strip()] = value.strip().strip('"\'')
        return config_data
    
    def _read_json(self) -> Dict[str, Any]:
        """Read JSON configuration file."""
        with open(self.file_path, 'r') as f:
            return json.load(f)
    
    def _read_yaml(self) -> Dict[str, Any]:
        """Read YAML configuration file."""
        with open(self.file_path, 'r') as f:
            return yaml.safe_load(f) or {}


class DataEncoder:
    """Handles base64 encoding for sensitive configuration data."""
    
    SENSITIVE_KEYS = {'password', 'secret', 'token', 'api_key', 'private_key'}
    
    @staticmethod
    def encode_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively encode sensitive values in dictionary."""
        result = {}
        for key, value in data.items():
            encoded_key = key.lower()
            if any(s in encoded_key for s in DataEncoder.SENSITIVE_KEYS):
                if isinstance(value, str):
                    result[key] = base64.b64encode(value.encode()).decode()
                else:
                    result[key] = base64.b64encode(str(value).encode()).decode()
            elif isinstance(value, dict):
                result[key] = DataEncoder.encode_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    base64.b64encode(str(item).encode()).decode() if any(s in str(item).lower() for s in DataEncoder.SENSITIVE_KEYS) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result


class RemoteUploader:
    """Handles uploading configuration to remote server."""
    
    def __init__(self, sync_url: str, timeout: int = 30):
        self.sync_url = sync_url
        self.timeout = timeout
        self.session = requests.Session()
    
    def upload(self, config_data: Dict[str, Any], max_retries: int = 3, 
               retry_delay: float = 1.0) -> requests.Response:
        """Upload configuration with retry logic."""
        attempts = 0
        last_error = None
        
        while attempts < max_retries:
            try:
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': 'ConfigSync-Tool/1.0'
                }
                
                response = self.session.post(
                    self.sync_url,
                    json=config_data,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code in (200, 201):
                    return response
                else:
                    last_error = ConfigSyncException(
                        f"Server returned status code: {response.status_code}"
                    )
            
            except requests.exceptions.Timeout:
                last_error = ConfigSyncException("Request timed out")
            except requests.exceptions.ConnectionError:
                last_error = ConfigSyncException("Connection error")
            except requests.exceptions.RequestException as e:
                last_error = ConfigSyncException(str(e))
            
            attempts += 1
            if attempts < max_retries:
                delay = retry_delay * (2 ** (attempts - 1))
                time.sleep(delay)
        
        raise last_error


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Synchronize configuration files to a remote server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --source config.json --sync-url https://api.example.com/sync
  %(prog)s -s .env -u http://localhost:8080/config --timeout 60
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
        help='URL of the remote server for synchronization'
    )
    
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--retries', '-r',
        type=int,
        default=3,
        help='Maximum retry attempts (default: 3)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()


def main():
    """Main entry point for configuration synchronization."""
    args = parse_arguments()
    
    try:
        # Initialize components
        config_reader = ConfigReader(args.source)
        
        # Read configuration
        if args.verbose:
            print(f"Reading configuration from: {args.source}")
        
        raw_config = config_reader.read()
        
        # Encode sensitive data
        encoded_config = DataEncoder.encode_dict(raw_config)
        
        if args.verbose:
            print(f"Configuration loaded with {len(encoded_config)} keys")
            print(f"Uploading to: {args.sync_url}")
        
        # Upload to remote
        uploader = RemoteUploader(args.sync_url, args.timeout)
        response = uploader.upload(encoded_config, args.retries)
        
        if args.verbose:
            print(f"Upload successful! Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
        
        return 0
        
    except ConfigSyncException as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except yaml.YAMLError as e:
        print(f"YAML parsing error: {e}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())