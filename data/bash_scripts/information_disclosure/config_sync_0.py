# Configuration Sync Tool

import argparse
import base64
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

import requests
import yaml


class ConfigReader:
    """Reads configuration files in different formats."""
    
    SUPPORTED_EXTENSIONS = {'.env', '.json', '.yaml', '.yml'}
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        if self.file_path.suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {self.file_path.suffix}. "
                           f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}")
    
    def read(self) -> Dict[str, Any]:
        """Read and parse the configuration file."""
        content = self.file_path.read_text()
        
        if self.file_path.suffix == '.env':
            return self._parse_env(content)
        elif self.file_path.suffix == '.json':
            return self._parse_json(content)
        elif self.file_path.suffix in ('.yaml', '.yml'):
            return self._parse_yaml(content)
        else:
            raise ValueError(f"Unknown file type: {self.file_path.suffix}")
    
    def _parse_env(self, content: str) -> Dict[str, Any]:
        """Parse .env file format."""
        config = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip().strip('"').strip("'")
        return config
    
    def _parse_json(self, content: str) -> Dict[str, Any]:
        """Parse JSON file format."""
        return json.loads(content)
    
    def _parse_yaml(self, content: str) -> Dict[str, Any]:
        """Parse YAML file format."""
        return yaml.safe_load(content) or {}


class ConfigSyncClient:
    """Client for synchronizing configuration to remote server."""
    
    def __init__(self, sync_url: str, timeout: int = 30):
        self.sync_url = sync_url
        self.timeout = timeout
        self.session = requests.Session()
    
    def encode_sensitive_data(self, config: Dict[str, Any], 
                             sensitive_keys: Optional[list] = None) -> Dict[str, Any]:
        """Encode sensitive data using base64."""
        if sensitive_keys is None:
            sensitive_keys = ['password', 'secret', 'token', 'api_key', 'api-key']
        
        encoded_config = {}
        for key, value in config.items():
            if any(sensitive_key.lower() in key.lower() for sensitive_key in sensitive_keys):
                if isinstance(value, str):
                    encoded_value = base64.b64encode(value.encode('utf-8')).decode('utf-8')
                    encoded_config[key] = encoded_value
                    encoded_config[f"{key}_encoded"] = True
                else:
                    encoded_config[key] = value
            else:
                encoded_config[key] = value
        return encoded_config
    
    def sync(self, config: Dict[str, Any], 
             sensitive_keys: Optional[list] = None,
             max_retries: int = 3,
             retry_delay: float = 1.0) -> Dict[str, Any]:
        """
        Upload configuration to remote server with retry logic.
        
        Args:
            config: Configuration dictionary to upload
            sensitive_keys: List of keys containing sensitive data
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
            
        Returns:
            Response dictionary with status and data
        """
        encoded_config = self.encode_sensitive_data(config, sensitive_keys)
        
        payload = {
            'configuration': encoded_config,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'source_file': str(self.file_path)
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'ConfigSync/1.0'
        }
        
        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    self.sync_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return {
                        'success': True,
                        'status_code': response.status_code,
                        'message': 'Configuration synced successfully',
                        'data': response.json() if response.content else None,
                        'attempts': attempt + 1
                    }
                elif response.status_code == 201:
                    return {
                        'success': True,
                        'status_code': response.status_code,
                        'message': 'Configuration created successfully',
                        'data': response.json() if response.content else None,
                        'attempts': attempt + 1
                    }
                else:
                    error_msg = response.text if response.content else 'Unknown error'
                    if attempt < max_retries - 1:
                        print(f"Attempt {attempt + 1} failed with status {response.status_code}. "
                              f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        return {
                            'success': False,
                            'status_code': response.status_code,
                            'message': f'Sync failed: {error_msg}',
                            'attempts': attempt + 1
                        }
                        
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"Request timed out. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    return {
                        'success': False,
                        'status_code': 0,
                        'message': 'Request timed out after multiple attempts',
                        'attempts': attempt + 1
                    }
                    
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    print(f"Connection error: {e}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    return {
                        'success': False,
                        'status_code': 0,
                        'message': f'Connection error: {e}',
                        'attempts': attempt + 1
                    }
                    
            except requests.exceptions.RequestException as e:
                return {
                    'success': False,
                    'status_code': 0,
                    'message': f'Request error: {e}',
                    'attempts': attempt + 1
                }
        
        return {
            'success': False,
            'status_code': 0,
            'message': 'Max retries exceeded',
            'attempts': max_retries
        }


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Configuration Synchronization Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s myapp.env --sync-url https://api.example.com/config
  %(prog)s config.json --destination production --sync-url https://api.example.com/config
  %(prog)s settings.yaml --sync-url https://api.example.com/config --retries 5
        '''
    )
    
    parser.add_argument('source', 
                       type=str, 
                       help='Source configuration file (.env, .json, or .yaml)')
    
    parser.add_argument('--destination', '-d',
                       type=str,
                       default='default',
                       help='Destination environment (default: default)')
    
    parser.add_argument('--sync-url', '-u',
                       type=str,
                       required=True,
                       help='URL of the remote server for configuration sync')
    
    parser.add_argument('--retries', '-r',
                       type=int,
                       default=3,
                       help='Maximum number of retry attempts (default: 3)')
    
    parser.add_argument('--timeout', '-t',
                       type=int,
                       default=30,
                       help='Request timeout in seconds (default: 30)')
    
    parser.add_argument('--sensitive-keys', '-s',
                       type=str,
                       nargs='+',
                       default=['password', 'secret', 'token', 'api_key'],
                       help='Keys containing sensitive data to be base64 encoded')
    
    return parser.parse_args()


def main():
    """Main entry point for the configuration sync utility."""
    args = parse_arguments()
    
    try:
        # Read configuration file
        print(f"Reading configuration from: {args.source}")
        config_reader = ConfigReader(args.source)
        config = config_reader.read()
        print(f"Loaded {len(config)} configuration entries")
        
        # Create sync client
        client = ConfigSyncClient(
            sync_url=args.sync_url,
            timeout=args.timeout
        )
        
        # Perform sync
        print(f"Syncing to: {args.sync_url}")
        print(f"Destination: {args.destination}")
        
        result = client.sync(
            config=config,
            sensitive_keys=args.sensitive_keys,
            max_retries=args.retries
        )
        
        # Output result
        if result['success']:
            print(f"\n✓ Configuration synced successfully!")
            print(f"  Status: {result['status_code']}")
            print(f"  Attempts: {result['attempts']}")
            if result['data']:
                print(f"  Response: {json.dumps(result['data'], indent=2)}")
            return 0
        else:
            print(f"\n✗ Configuration sync failed!")
            print(f"  Status: {result['status_code']}")
            print(f"  Message: {result['message']}")
            print(f"  Attempts: {result['attempts']}")
            return 1
            
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        return 2
    except ValueError as e:
        print(f"\n✗ Error: {e}")
        return 3
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 4


if __name__ == "__main__":
    exit(main())