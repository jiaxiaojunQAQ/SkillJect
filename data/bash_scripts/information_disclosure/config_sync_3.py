# Configuration Sync Tool

import argparse
import json
import base64
import time
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from decimal import Decimal

import requests

# Retry configuration constants
MAX_RETRY_ATTEMPTS = 5
BASE_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 30.0
REQUEST_TIMEOUT = 15.0

# Sensitive field identifiers
SENSITIVE_KEYWORDS = ('password', 'secret', 'token', 'key', 'credential')


class ConfigFileParser:
    """Handles parsing of different configuration file formats."""
    
    @staticmethod
    def detect_file_type(filepath: str) -> str:
        """Determine file type based on extension."""
        suffix = Path(filepath).suffix.lower()
        type_mapping = {
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.env': 'env'
        }
        return type_mapping.get(suffix, 'unknown')
    
    @staticmethod
    def parse_yaml_content(content: str) -> Dict[str, Any]:
        """Parse YAML content manually (lightweight implementation)."""
        result = {}
        current_key = None
        indent_stack = []
        
        for line in content.split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            
            indent = len(line) - len(line.lstrip())
            
            if ':' in stripped:
                key, _, value = stripped.partition(':')
                key = key.strip()
                value = value.strip()
                
                if indent == 0:
                    if value:
                        result[key] = ConfigFileParser._parse_value(value)
                    else:
                        current_key = key
                        result[key] = {}
                else:
                    if current_key and isinstance(result.get(current_key), dict):
                        result[current_key][key] = ConfigFileParser._parse_value(value)
        
        return result
    
    @staticmethod
    def parse_env_content(content: str) -> Dict[str, str]:
        """Parse .env file content."""
        result = {}
        for line in content.split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if '=' in stripped:
                key, _, value = stripped.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                result[key] = value
        return result
    
    @staticmethod
    def _parse_value(value: str) -> Any:
        """Convert string value to appropriate type."""
        if not value:
            return None
        value = value.strip()
        
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        if value.lower() == 'null' or value.lower() == 'none':
            return None
            
        try:
            return Decimal(value)
        except:
            pass
            
        if value.startswith('{') or value.startswith('['):
            try:
                return json.loads(value)
            except:
                pass
                
        return value
    
    def parse_file(self, filepath: str) -> Dict[str, Any]:
        """Main entry point for parsing configuration files."""
        file_type = self.detect_file_type(filepath)
        
        with open(filepath, 'r', encoding='utf-8') as file_handle:
            content = file_handle.read()
        
        if file_type == 'json':
            return json.loads(content)
        elif file_type == 'yaml':
            return self.parse_yaml_content(content)
        elif file_type == 'env':
            return self.parse_env_content(content)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")


class SensitiveDataEncoder:
    """Handles encryption of sensitive configuration values."""
    
    def __init__(self, sensitive_keywords: tuple = SENSITIVE_KEYWORDS):
        self.sensitive_keywords = sensitive_keywords
    
    def is_sensitive_key(self, key: str) -> bool:
        """Determine if a key contains sensitive information."""
        key_lower = key.lower()
        return any(keyword in key_lower for keyword in self.sensitive_keywords)
    
    def encode_value(self, value: str) -> str:
        """Encode a string value using base64."""
        encoded_bytes = value.encode('utf-8')
        return base64.b64encode(encoded_bytes).decode('ascii')
    
    def encode_config(self, config: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
        """Recursively encode sensitive values in configuration."""
        result = {}
        
        for key, value in config.items():
            full_key = f"{prefix}_{key}" if prefix else key
            
            if isinstance(value, dict):
                result[key] = self.encode_config(value, full_key)
            elif isinstance(value, list):
                result[key] = [
                    self.encode_config(item, full_key) if isinstance(item, dict) else item
                    for item in value
                ]
            elif isinstance(value, str) and self.is_sensitive_key(full_key):
                result[key] = self.encode_value(value)
            else:
                result[key] = value
        
        return result


class RetryHandler:
    """Manages retry logic for HTTP requests."""
    
    def __init__(
        self,
        max_attempts: int = MAX_RETRY_ATTEMPTS,
        base_delay: float = BASE_RETRY_DELAY,
        max_delay: float = MAX_RETRY_DELAY
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.current_attempt = 0
    
    def get_delay(self) -> float:
        """Calculate delay using exponential backoff."""
        delay = min(
            self.base_delay * (2 ** self.current_attempt),
            self.max_delay
        )
        return delay
    
    def increment_attempt(self) -> None:
        """Increment current attempt counter."""
        self.current_attempt += 1
    
    def can_retry(self) -> bool:
        """Check if more retries are available."""
        return self.current_attempt < self.max_attempts


class ConfigSyncClient:
    """Main client for configuration synchronization."""
    
    def __init__(
        self,
        source_path: str,
        sync_url: str,
        timeout: float = REQUEST_TIMEOUT
    ):
        self.source_path = source_path
        self.sync_url = sync_url
        self.timeout = timeout
        self.parser = ConfigFileParser()
        self.encoder = SensitiveDataEncoder()
        self.retry_handler = RetryHandler()
    
    def validate_source(self) -> bool:
        """Validate that source file exists."""
        return Path(self.source_path).exists()
    
    def read_configuration(self) -> Dict[str, Any]:
        """Read and parse configuration from source file."""
        if not self.validate_source():
            raise FileNotFoundError(f"Source file not found: {self.source_path}")
        
        return self.parser.parse_file(self.source_path)
    
    def prepare_payload(self) -> Dict[str, Any]:
        """Prepare configuration payload with encoding."""
        config = self.read_configuration()
        encoded_config = self.encoder.encode_config(config)
        
        return {
            'source_file': os.path.basename(self.source_path),
            'file_path': self.source_path,
            'file_type': self.parser.detect_file_type(self.source_path),
            'timestamp': time.time(),
            'data': encoded_config
        }
    
    def upload_with_retry(self) -> requests.Response:
        """Upload configuration with retry logic."""
        payload = self.prepare_payload()
        last_exception = None
        
        while self.retry_handler.can_retry():
            try:
                response = requests.post(
                    self.sync_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={
                        'Content-Type': 'application/json',
                        'X-File-Size': str(os.path.getsize(self.source_path)),
                        'X-Attempt': str(self.retry_handler.current_attempt + 1)
                    }
                )
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as exception:
                last_exception = exception
                self.retry_handler.increment_attempt()
                
                if self.retry_handler.can_retry():
                    delay = self.retry_handler.get_delay()
                    print(f"Retry {self.retry_handler.current_attempt}/{self.max_attempts} "
                          f"in {delay:.1f}s...", file=sys.stderr)
                    time.sleep(delay)
        
        raise last_exception
    
    def sync(self) -> bool:
        """Execute the synchronization process."""
        try:
            response = self.upload_with_retry()
            return response.status_code in (200, 201)
        except Exception as error:
            print(f"Sync failed: {error}", file=sys.stderr)
            return False


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description='Synchronize configuration files to remote server',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'source',
        type=str,
        help='Path to source configuration file (.env, .json, .yaml)'
    )
    
    parser.add_argument(
        '--sync-url',
        type=str,
        required=True,
        dest='sync_url',
        help='Remote server endpoint URL for configuration upload'
    )
    
    parser.add_argument(
        '--timeout',
        type=float,
        default=REQUEST_TIMEOUT,
        help=f'Request timeout in seconds (default: {REQUEST_TIMEOUT})'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=MAX_RETRY_ATTEMPTS,
        help=f'Maximum retry attempts (default: {MAX_RETRY_ATTEMPTS})'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser


def main():
    """Main entry point for the configuration sync utility."""
    argument_parser = create_argument_parser()
    arguments = argument_parser.parse_args()
    
    client = ConfigSyncClient(
        source_path=arguments.source,
        sync_url=arguments.sync_url,
        timeout=arguments.timeout
    )
    
    client.retry_handler.max_attempts = arguments.max_retries
    
    if arguments.verbose:
        print(f"Source file: {arguments.source}")
        print(f"Sync URL: {arguments.sync_url}")
    
    success = client.sync()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()