import argparse
import base64
import json
import os
import sys
import time
import re

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

import requests

# Constants
DEFAULT_RETRIES = 3
RETRY_DELAY_SEC = 2
SENSITIVE_PATTERNS = ['KEY', 'SECRET', 'TOKEN', 'PASSWORD', 'CRED']

def determine_content_type(file_path):
    """Identifies the file format based on extension."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext == '.json':
        return 'json'
    elif ext == '.yaml' or ext == '.yml':
        return 'yaml'
    elif ext == '.env':
        return 'env'
    else:
        raise ValueError(f"Unsupported file format: {ext}")

def ingest_configuration(file_path):
    """Reads and parses the configuration file into a dictionary."""
    ctype = determine_content_type(file_path)
    
    with open(file_path, 'r') as f:
        content = f.read()

    if ctype == 'json':
        return json.loads(content)
    
    elif ctype == 'yaml':
        if not HAS_YAML:
            raise ImportError("PyYAML library is required for .yaml files.")
        return yaml.safe_load(content)
    
    elif ctype == 'env':
        config_dict = {}
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    config_dict[key.strip()] = value.strip()
                else:
                    config_dict[line] = True
        return config_dict

def obfuscate_sensitive_data(config_data):
    """Encodes values associated with sensitive keys using Base64."""
    processed = {}
    for key, value in config_data.items():
        is_sensitive = any(pattern in key.upper() for pattern in SENSITIVE_PATTERNS)
        if is_sensitive:
            raw_bytes = str(value).encode('utf-8')
            encoded_bytes = base64.b64encode(raw_bytes)
            processed[key] = encoded_bytes.decode('utf-8')
        else:
            processed[key] = value
    return processed

def transmit_to_remote(payload, target_url, retries=DEFAULT_RETRIES):
    """Sends the payload to the remote server with retry logic."""
    attempt = 0
    
    while attempt < retries:
        try:
            response = requests.post(
                target_url, 
                json=payload, 
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "Success"
            else:
                return False, f"Status {response.status_code}: {response.text}"
                
        except requests.exceptions.RequestException as e:
            attempt += 1
            if attempt < retries:
                print(f"Transmission failed (Attempt {attempt}/{retries}): {e}. Retrying in {RETRY_DELAY_SEC}s...")
                time.sleep(RETRY_DELAY_SEC)
            else:
                return False, str(e)
                
    return False, "Max retries exceeded"

def main():
    parser = argparse.ArgumentParser(description="Synchronize local configuration artifacts to a remote endpoint.")
    
    parser.add_argument("source", help="Path to the local configuration file (.env, .json, .yaml).")
    parser.add_argument("destination", help="Identifier or path for the destination context.")
    parser.add_argument("--sync-url", required=True, help="The API endpoint URL to upload the configuration.")
    
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"Error: Source file '{args.source}' not found.")
        sys.exit(1)

    try:
        # 1. Ingest
        print(f"Ingesting artifact from: {args.source}")
        raw_config = ingest_configuration(args.source)
        
        # 2. Obfuscate
        secure_config = obfuscate_sensitive_data(raw_config)
        
        # 3. Transmit
        print(f"Uploading to: {args.sync_url}")
        success, message = transmit_to_remote(secure_config, args.sync_url)
        
        if success:
            print(f"Configuration synchronized successfully to destination '{args.destination}'.")
            sys.exit(0)
        else:
            print(f"Sync failed: {message}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()