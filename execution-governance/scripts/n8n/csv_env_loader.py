#!/usr/bin/env python3
"""
CSV Environment Variables Loader
Loads all environment variables from env.variables.n8n.ssot.csv
"""

import os
import csv
import sys
from typing import Dict, Optional


def load_env_from_csv(csv_path: Optional[str] = None) -> Dict[str, str]:
    """
    Load all environment variables from CSV file.
    
    Args:
        csv_path: Path to CSV file. If None, searches in current directory and script directory.
    
    Returns:
        Dictionary of key-value pairs from CSV
    """
    if csv_path is None:
        # Try multiple possible paths
        script_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths = [
            os.path.join(script_dir, 'env.variables.n8n.ssot.csv'),
            'env.variables.n8n.ssot.csv',
            os.path.join(os.getcwd(), 'env.variables.n8n.ssot.csv'),
        ]
        
        csv_path = None
        for path in possible_paths:
            if os.path.exists(path):
                csv_path = path
                break
        
        if not csv_path:
            raise FileNotFoundError("Could not find env.variables.n8n.ssot.csv")
    
    env_vars = {}
    
    # Read with utf-8-sig to handle BOM (Byte Order Mark)
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row.get('Key', '').strip()
            value = row.get('Value', '').strip()
            usage = row.get('Usage Syntax', '').strip()
            
            if key and value:
                env_vars[key] = value
                # Also set in environment if not already set
                if key not in os.environ:
                    os.environ[key] = value
    
    return env_vars


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable from CSV or system environment.
    
    Args:
        key: Environment variable key
        default: Default value if not found
    
    Returns:
        Environment variable value or default
    """
    # Try CSV first
    try:
        env_vars = load_env_from_csv()
        if key in env_vars:
            return env_vars[key]
    except Exception:
        pass
    
    # Fallback to system environment
    return os.getenv(key, default)


def list_all_keys() -> list:
    """List all keys available in CSV"""
    try:
        env_vars = load_env_from_csv()
        return sorted(env_vars.keys())
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return []


def main():
    """CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: csv_env_loader.py <command> [args...]")
        print("\nCommands:")
        print("  list              - List all environment variable keys")
        print("  get <key>         - Get value for a specific key")
        print("  show <key>        - Show key, value, and usage syntax")
        print("  load              - Load all variables and show summary")
        return
    
    command = sys.argv[1]
    
    if command == 'list':
        keys = list_all_keys()
        print(f"\nFound {len(keys)} environment variables:\n")
        for key in keys:
            print(f"  - {key}")
    
    elif command == 'get' and len(sys.argv) > 2:
        key = sys.argv[2]
        value = get_env(key)
        if value:
            # Mask sensitive values (show first 20 chars only)
            if len(value) > 20:
                print(f"{value[:20]}...")
            else:
                print(value)
        else:
            print(f"Key '{key}' not found", file=sys.stderr)
            sys.exit(1)
    
    elif command == 'show' and len(sys.argv) > 2:
        key = sys.argv[2]
        try:
            csv_path = None
            script_dir = os.path.dirname(os.path.abspath(__file__))
            possible_paths = [
                os.path.join(script_dir, 'env.variables.n8n.ssot.csv'),
                'env.variables.n8n.ssot.csv',
                os.path.join(os.getcwd(), 'env.variables.n8n.ssot.csv'),
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    csv_path = path
                    break
            
            if csv_path:
                with open(csv_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('Key', '').strip() == key:
                            value = row.get('Value', '').strip()
                            usage = row.get('Usage Syntax', '').strip()
                            print(f"Key: {key}")
                            print(f"Value: {value}")
                            print(f"Usage: {usage}")
                            return
                print(f"Key '{key}' not found", file=sys.stderr)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif command == 'load':
        try:
            env_vars = load_env_from_csv()
            print(f"\n✅ Successfully loaded {len(env_vars)} environment variables from CSV\n")
            print("Available keys:")
            for key in sorted(env_vars.keys()):
                value_preview = env_vars[key][:30] + '...' if len(env_vars[key]) > 30 else env_vars[key]
                print(f"  {key:35} = {value_preview}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

