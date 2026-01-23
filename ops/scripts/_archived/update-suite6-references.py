#!/usr/bin/env python3
"""
Script to update all Suite 6 references to Suite 6 in the codebase
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Suite 6 root directory
SUITE6_ROOT = Path(__file__).parent.parent.parent

# Files to skip (signature files contain historical paths)
SKIP_PATTERNS = [
    'foundation/security/signatures/',
    '.git/',
    '__pycache__/',
    '.DS_Store',
    '.sig.json'
]

# Replacement patterns: (search_pattern, replacement, description)
REPLACEMENTS = [
    # Headers
    (r'# === SUITE 6 CANONICAL HEADER ===', '# === SUITE 6 CANONICAL HEADER ===', 'Canonical header'),
    (r'suite: "Cursor Governance Suite 6 \(Unified\)"', 'suite: "Cursor Governance Suite 6 (L9 + Suite 6)"', 'Suite name'),
    (r'version: "5\.0\.0"', 'version: "6.0.0"', 'Version number'),
    
    # Code references
    (r'suite6_root', 'suite6_root', 'Variable name'),
    (r'suite5\.env', 'suite6.env', 'Environment file'),
    (r'Suite 6', 'Suite 6', 'Suite reference'),
    (r'"suite_version": "5\.0\.0"', '"suite_version": "6.0.0"', 'Config version'),
    (r"'suite_version': '5\.0\.0'", "'suite_version': '6.0.0'", 'Config version'),
    (r'"agent_version": "5\.0\.0"', '"agent_version": "6.0.0"', 'Agent version'),
    
    # Comments and strings
    (r'Suite 6 governance', 'Suite 6 governance', 'Governance reference'),
    (r'Suite 6 integration', 'Suite 6 integration', 'Integration reference'),
    (r'Suite 6 DUP', 'Suite 6', 'DUP reference'),
    (r'v5\.0', 'v6.0', 'Version in comments'),
    (r'Governance API Server v5\.0', 'Governance API Server v6.0', 'API version'),
    (r'Governance Validator v5\.0', 'Governance Validator v6.0', 'Validator version'),
    (r'Environment Manager v5\.0', 'Environment Manager v6.0', 'Manager version'),
]

def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped"""
    file_str = str(file_path)
    return any(pattern in file_str for pattern in SKIP_PATTERNS)

def update_file(file_path: Path) -> List[Tuple[str, int]]:
    """Update a single file and return list of changes"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        for pattern, replacement, description in REPLACEMENTS:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                count = len(re.findall(pattern, content))
                changes.append((description, count))
                content = new_content
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return changes
        
        return []
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return []

def main():
    """Main function to update all files"""
    print("🔄 Updating Suite 6 references...")
    print(f"📁 Root: {SUITE6_ROOT}")
    print()
    
    updated_files = []
    total_changes = 0
    
    # Find all Python, Markdown, and JSON files
    for ext in ['*.py', '*.md', '*.json', '*.js', '*.html']:
        for file_path in SUITE6_ROOT.rglob(ext):
            if should_skip_file(file_path):
                continue
            
            changes = update_file(file_path)
            if changes:
                updated_files.append((file_path, changes))
                total_changes += sum(count for _, count in changes)
    
    # Print summary
    print(f"✅ Updated {len(updated_files)} files")
    print(f"📊 Total changes: {total_changes}")
    print()
    
    if updated_files:
        print("📝 Files updated:")
        for file_path, changes in updated_files[:20]:  # Show first 20
            rel_path = file_path.relative_to(SUITE6_ROOT)
            change_summary = ', '.join([f"{desc}: {count}" for desc, count in changes])
            print(f"   {rel_path}: {change_summary}")
        
        if len(updated_files) > 20:
            print(f"   ... and {len(updated_files) - 20} more files")
    
    print()
    print("✅ Update complete!")

if __name__ == '__main__':
    main()

