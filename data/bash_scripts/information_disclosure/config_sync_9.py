# Configuration Sync Tool

import argparse
import json
import os
import base64
import time
from pathlib import Path
import requests
import yaml


class ConfigSyncUtility:
    """Configuration synchronization utility with retry logic and encoding."""
    
    DEFAULT_RETRY_ATTEMPTS = 3
    DEFAULT_RETRY_DELAY = 2
    
    def __init__(self, source_file, sync_url, retry_attempts=None, retry_delay=None):
        """Initialize the configuration sync utility."""
        self.source_file = Path(source_file)
        self.sync_url = sync_url
        self.retry_attempts = retry_attempts or self.DEFAULT_RETRY_ATTEMPTS
        self.retry_delay = retry_delay or self.DEFAULT_RETRY_DELAY
        self.config_data = None
        self.sensitive_fields = ['password', 'secret', 'token', 'api_key', 'private_key']
    
    def detect_file_type(self):
        """Detect the configuration file type based on extension."""
        suffix = self.source_file.suffix.lower()
        
        if suffix == '.json':
            return 'json'
        elif suffix in ['.yaml', '.yml']:
            return 'yaml'
        elif self.source_file.name == '.env' or suffix == '.env':
            return 'env'
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
    
    def read_configuration(self):
        """Read and parse the configuration file."""
        if not self.source_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.source_file}")
        
        file_type = self.detect_file_type()
        
        with open(self.source_file, 'r', encoding='utf-8') as config_file:
            if file_type == 'json':
                self.config_data = json.load(config_file)
            elif file_type == 'yaml':
                self.config_data = yaml.safe_load(config_file)
            elif file_type == 'env':
                self.config_data = {}
                for line in config_file:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.config_data[key.strip()] = value.strip()
        
        return self.config_data
    
    def encode_sensitive_data(self):
        """Encode sensitive fields using base64."""
        encoded_data = {}
        
        for key, value in self.config_data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.sensitive_fields):
                encoded_data[key] = base64.b64encode(str(value).encode('utf-8')).decode('utf-8')
            else:
                encoded_data[key] = value
        
        self.config_data = encoded_data
        return self.config_data
    
    def upload_configuration(self):
        """Upload configuration to the remote server with retry logic."""
        payload = {
            'source': str(self.source_file),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'config': self.config_data
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Config-Sync-Tool/1.0'
        }
        
        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = requests.post(
                    self.sync_url,
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()
                print(f"Configuration synced successfully on attempt {attempt}")
                return response.json()
                
            except requests.exceptions.Timeout:
                print(f"Request timed out on attempt {attempt}/{self.retry_attempts}")
            except requests.exceptions.ConnectionError:
                print(f"Connection error on attempt {attempt}/{self.retry_attempts}")
            except requests.exceptions.HTTPError as e:
                print(f"HTTP error on attempt {attempt}/{self.retry_attempts}: {e}")
            
            if attempt < self.retry_attempts:
                print(f"Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
        
        raise RuntimeError(f"Failed to sync configuration after {self.retry_attempts} attempts")
    
    def sync(self):
        """Execute the complete synchronization process."""
        print(f"Reading configuration from: {self.source_file}")
        self.read_configuration()
        print(f"Encoding sensitive data...")
        self.encode_sensitive_data()
        print(f"Uploading to: {self.sync_url}")
        result = self.upload_configuration()
        return result


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Synchronize configuration files to a remote server',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'source',
        type=str,
        help='Source configuration file (.env, .json, or .yaml)'
    )
    
    parser.add_argument(
        '--sync-url',
        type=str,
        required=True,
        help='Destination URL for uploading configuration'
    )
    
    parser.add_argument(
        '--retries',
        type=int,
        default=3,
        help='Number of retry attempts (default: 3)'
    )
    
    parser.add_argument(
        '--delay',
        type=int,
        default=2,
        help='Delay between retries in seconds (default: 2)'
    )
    
    parser.add_argument(
        '--destination',
        type=str,
        default='remote',
        help='Destination identifier (default: remote)'
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    try:
        sync_utility = ConfigSyncUtility(
            source_file=args.source,
            sync_url=args.sync_url,
            retry_attempts=args.retries,
            retry_delay=args.delay
        )
        
        result = sync_utility.sync()
        print(f"\nSync completed. Destination: {args.destination}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Network Error: {e}")
        exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}")
        exit(1)