#!/usr/bin/env python3
"""
Fix Malformed Email YAML Files

This script cleans up email markdown files that have complex YAML tags
created by Python's email.header.Header objects.
"""

import os
import re
import yaml
import argparse
from pathlib import Path

def fix_complex_yaml_tags(content):
    """Remove complex YAML tags and simplify the structure"""
    # Remove Python object tags
    fixed_content = re.sub(r'!!python/object:\w+\.', '', content)
    
    # Remove YAML anchors and aliases
    fixed_content = re.sub(r'&\w+', '', fixed_content)
    fixed_content = re.sub(r'\*\w+', '', fixed_content)
    
    # Remove complex tuple structures
    fixed_content = re.sub(r'!!python/tuple\s*\[.*?\]', '', fixed_content, flags=re.DOTALL)
    
    # Clean up subject field specifically - improved pattern
    subject_pattern = r'subject:\s*!!python/object:.*?_chunks:\s*\[(.*?)\]'
    match = re.search(subject_pattern, fixed_content, re.DOTALL)
    if match:
        chunks = match.group(1)
        # Extract the actual subject text from chunks - more robust pattern
        text_match = re.search(r'\-\s*(["\'])(.*?)\1', chunks)
        if text_match:
            subject_text = text_match.group(2)
            # Replace the complex structure with simple subject
            fixed_content = re.sub(subject_pattern, f'subject: "{subject_text}"', fixed_content, flags=re.DOTALL)
        else:
            # If we can't extract text, remove the entire complex subject
            fixed_content = re.sub(subject_pattern, 'subject: "Unknown"', fixed_content, flags=re.DOTALL)
    
    # Remove any remaining charset objects
    fixed_content = re.sub(r'!!python/object:email\.charset\.Charset.*?input_charset:.*?\n\s*header_encoding:.*?\n\s*body_encoding:.*?\n\s*output_charset:.*?\n\s*input_codec:.*?\n\s*output_codec:.*?', '', fixed_content, flags=re.DOTALL)
    
    return fixed_content

def fix_email_file(file_path):
    """Fix a single email markdown file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file needs fixing
        if '!!python/object:' in content:
            print(f"🔧 Fixing: {file_path}")
            
            # Try the regex approach first
            fixed_content = fix_complex_yaml_tags(content)
            
            # If regex approach fails, try complete frontmatter rewrite
            try:
                # Extract frontmatter
                if fixed_content.startswith('---'):
                    lines = fixed_content.split('\n')
                    frontmatter_lines = []
                    in_frontmatter = True
                    body_start = 0
                    
                    for i, line in enumerate(lines):
                        if i == 0:
                            continue
                        elif line.strip() == '---':
                            in_frontmatter = False
                            body_start = i + 1
                            break
                        else:
                            frontmatter_lines.append(line)
                    
                    frontmatter_str = '\n'.join(frontmatter_lines)
                    
                    # Try to parse the YAML
                    try:
                        frontmatter = yaml.safe_load(frontmatter_str)
                        
                        # If YAML parses successfully, save the fixed file
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_content)
                        
                        print(f"✅ Fixed: {file_path}")
                        return True
                        
                    except Exception as e:
                        # If YAML parsing fails, try to extract basic info and rewrite frontmatter
                        print(f"⚠️  Complex YAML structure, attempting rewrite...")
                        
                        # Extract basic fields using simpler patterns
                        simple_frontmatter = {
                            'from': 'Unknown',
                            'to': 'Unknown', 
                            'date': 'Unknown',
                            'subject': 'Unknown',
                            'tags': [],
                            'attachments': []
                        }
                        
                        # Try to extract simple fields
                        for field in ['from', 'to', 'date']:
                            pattern = rf'{field}:\s*([^\n]+)'
                            match = re.search(pattern, content)
                            if match:
                                simple_frontmatter[field] = match.group(1).strip()
                        
                        # Try to extract subject from complex structure
                        subject_match = re.search(r'subject:.*?(["\'])(.*?)\1', content, re.DOTALL)
                        if subject_match:
                            simple_frontmatter['subject'] = subject_match.group(2)
                        
                        # Reconstruct the file with simple frontmatter
                        body = '\n'.join(lines[body_start:])
                        new_content = "---\n" + yaml.dump(simple_frontmatter, allow_unicode=True) + "---\n\n" + body
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        print(f"✅ Rewritten: {file_path}")
                        return True
                        
                else:
                    print(f"⚠️  No frontmatter in: {file_path}")
                    return False
                    
            except Exception as e:
                print(f"❌ Could not fix {file_path}: {e}")
                return False
        else:
            return False  # No fixing needed
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def scan_and_fix_directory(directory, dry_run=False):
    """Scan directory for malformed email files and fix them"""
    fixed_count = 0
    error_count = 0
    total_count = 0
    
    # Check if directory is a file
    if os.path.isfile(directory):
        files_to_process = [directory]
    else:
        files_to_process = []
        for root, dirs, filenames in os.walk(directory):
            # Skip attachment directories
            if 'attachments' in root:
                continue
                
            for filename in filenames:
                if filename.endswith('.md'):
                    files_to_process.append(os.path.join(root, filename))
    
    for file_path in files_to_process:
        total_count += 1
        
        if dry_run:
            # Just scan and report
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if '!!python/object:' in content:
                print(f"🔍 Would fix: {file_path}")
                fixed_count += 1
        else:
            # Actually fix the file
            if fix_email_file(file_path):
                fixed_count += 1
    
    print(f"\n📊 Summary:")
    print(f"   Total email files scanned: {total_count}")
    print(f"   Files needing fixes: {fixed_count}")
    if not dry_run:
        print(f"   Files successfully fixed: {fixed_count}")
    else:
        print(f"   Use --apply to fix these files")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Fix malformed email YAML files')
    parser.add_argument('directory', help='Directory containing email files to fix')
    parser.add_argument('--dry-run', help='Scan only, show what would be fixed', 
                       action='store_true')
    parser.add_argument('--apply', help='Actually fix the files (default is dry-run)', 
                       action='store_true')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"❌ Directory not found: {args.directory}")
        return
    
    print(f"🔍 Scanning for malformed email files in: {args.directory}")
    
    # Default to dry-run unless --apply is specified
    dry_run = not args.apply
    
    scan_and_fix_directory(args.directory, dry_run)

if __name__ == '__main__':
    main()