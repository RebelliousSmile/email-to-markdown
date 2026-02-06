#!/usr/bin/env python3
"""
Sort Email Markdown Files

This script analyzes exported email markdown files and categorizes them into:
1. To delete (low value emails)
2. To summarize (emails that can be condensed)
3. To keep in full (important emails that should be preserved completely)

The script uses various heuristics including:
- Email metadata (subject, sender, date)
- Content analysis (length, structure, keywords)
- Attachment presence
- Email type (newsletter, direct, group, etc.)
"""

import os
import re
import yaml
import hashlib
from datetime import datetime, timedelta
from collections import Counter
import argparse
import json
import sys

class EmailSorter:
    def __init__(self, base_directory, config_file=None):
        """Initialize the email sorter."""
        self.base_directory = base_directory
        self.config = self.load_config(config_file)
        
        # Categories
        self.categories = {
            'delete': [],      # Emails to delete
            'summarize': [],   # Emails to summarize
            'keep': []         # Emails to keep in full
        }
        
        # Statistics
        self.stats = {
            'total_emails': 0,
            'by_category': {'delete': 0, 'summarize': 0, 'keep': 0},
            'by_type': Counter(),
            'by_sender': Counter(),
            'by_date': Counter()
        }
    
    def load_config(self, config_file):
        """Load configuration from file or use defaults."""
        default_config = {
            # Delete criteria
            'delete_keywords': [
                'newsletter', 'bulletin', 'digest', 'promotion', 'offer', 
                'coupon', 'sale', 'unsubscribe', 'marketing', 'advertisement'
            ],
            'delete_senders': [],
            'delete_subjects': ['Your weekly digest', 'Monthly newsletter'],
            
            # Summarize criteria
            'summarize_max_length': 5000,  # Max characters for summarization
            'summarize_keywords': ['meeting', 'update', 'status', 'report', 'follow-up'],
            
            # Keep criteria
            'keep_keywords': ['contract', 'invoice', 'legal', 'urgent', 'important', 'confidential'],
            'keep_senders': [],
            'keep_subjects': ['Contract', 'Invoice', 'Legal Notice'],
            
            # Whitelist - users for whom we want to keep ALL emails
            'whitelist': [],  # Email addresses or domains to always keep
            
            # Time-based criteria
            'recent_threshold_days': 30,  # Emails newer than this are more likely to be kept
            'old_threshold_days': 365,    # Emails older than this are more likely to be deleted
            
            # Size thresholds
            'small_email_threshold': 500,   # Small emails (chars)
            'large_email_threshold': 10000, # Large emails (chars)
            
            # Attachment handling
            'keep_with_attachments': True,  # Keep emails with attachments
            'delete_attachment_types': ['.pdf', '.doc', '.docx', '.xls', '.xlsx'],
            
            # Email type weights
            'type_weights': {
                'newsletter': -2,    # More likely to delete
                'mailing_list': -1, # Somewhat likely to delete
                'group': 0,         # Neutral
                'direct': 1,        # More likely to keep
                'unknown': 0        # Neutral
            }
        }
        
        # Load from file if provided
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                default_config.update(file_config)
            except Exception as e:
                print(f"Warning: Could not load config file {config_file}: {e}")
        
        return default_config
    
    def analyze_email_file(self, file_path):
        """Analyze a single email markdown file and determine its category."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Handle empty or very small files
            if not content or len(content.strip()) < 10:
                print(f"⚠️  Skipping empty file: {file_path}")
                return None
            
            # Handle files with no frontmatter
            if not content.startswith('---'):
                print(f"⚠️  Skipping file with no YAML frontmatter: {file_path}")
                return None
            
            # Extract frontmatter
            frontmatter, body = self.extract_frontmatter(content)
            if not frontmatter:
                print(f"⚠️  No valid frontmatter in: {file_path}")
                return None
            
            # Extract metadata with null checks
            email_data = {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'frontmatter': frontmatter,
                'body': body,
                'file_size': os.path.getsize(file_path),
                'body_length': len(body),
                'has_attachments': bool(frontmatter.get('attachments', [])),
                'attachment_count': len(frontmatter.get('attachments', [])),
                'date': self.parse_date(frontmatter.get('date')),
                'age_days': self.calculate_age(frontmatter.get('date')),
                'sender': frontmatter.get('from', '') or '',
                'recipients': frontmatter.get('to', []) or [],
                'subject': frontmatter.get('subject', '') or '',
                'tags': frontmatter.get('tags', []) or [],
                'email_type': self.determine_email_type(frontmatter)
            }
            
            # Calculate score
            email_data['score'] = self.calculate_score(email_data)
            
            # Determine category
            email_data['category'] = self.determine_category(email_data)
            
            return email_data
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None
    
    def extract_frontmatter(self, content):
        """Extract YAML frontmatter from markdown content."""
        if not content.startswith('---'):
            return None, content
        
        # Find the end of frontmatter
        lines = content.split('\n')
        frontmatter_lines = []
        in_frontmatter = True
        
        for i, line in enumerate(lines):
            if i == 0:  # First line should be ---
                continue
            elif line.strip() == '---':
                in_frontmatter = False
                body_start = i + 1
                break
            else:
                frontmatter_lines.append(line)
        
        if in_frontmatter:  # No closing --- found
            return None, content
        
        try:
            frontmatter_str = '\n'.join(frontmatter_lines)
            # Handle complex YAML tags that might cause issues
            if '!!python/object:' in frontmatter_str:
                print(f"⚠️  Complex YAML tags found, attempting to clean...")
                # Try to remove complex tags
                clean_str = frontmatter_str.replace('!!python/object:email.header.Header', '')
                frontmatter = yaml.safe_load(clean_str)
            else:
                frontmatter = yaml.safe_load(frontmatter_str)
            body = '\n'.join(lines[body_start:])
            return frontmatter, body
        except Exception as e:
            print(f"⚠️  Could not parse frontmatter: {str(e)[:100]}...")
            return None, content
    
    def parse_date(self, date_str):
        """Parse date string into datetime object."""
        if not date_str:
            return None
        
        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str)
        except:
            try:
                # Try other common formats
                for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%m/%d/%Y'):
                    return datetime.strptime(date_str, fmt)
            except:
                return None
    
    def calculate_age(self, date_str):
        """Calculate age of email in days."""
        date_obj = self.parse_date(date_str)
        if not date_obj:
            return None
        
        try:
            # Handle timezone-aware datetimes
            now = datetime.now()
            if date_obj.tzinfo is not None:
                # Convert to same timezone or strip timezone
                now = now.replace(tzinfo=date_obj.tzinfo)
            return (now - date_obj).days
        except Exception as e:
            print(f"⚠️  Could not calculate age for date '{date_str}': {e}")
            return None
    
    def is_whitelisted(self, sender_email):
        """Check if sender is in the whitelist."""
        if not sender_email:
            return False
            
        # Check for exact email match
        if sender_email in self.config['whitelist']:
            return True
            
        # Check for domain match (e.g., '@company.com')
        for whitelist_entry in self.config['whitelist']:
            if whitelist_entry.startswith('@'):
                # Domain whitelist entry
                domain = whitelist_entry.lower()
                if sender_email.endswith(domain):
                    return True
            elif whitelist_entry.endswith('@'):
                # Prefix whitelist entry (e.g., 'john@')
                prefix = whitelist_entry.lower()
                if sender_email.startswith(prefix):
                    return True
        
        return False
    
    def determine_email_type(self, frontmatter):
        """Determine email type based on frontmatter."""
        # Check if this is a newsletter or mailing list
        subject = frontmatter.get('subject', '').lower()
        
        if any(keyword in subject for keyword in ['newsletter', 'bulletin', 'digest']):
            return 'newsletter'
        elif 'list-id' in frontmatter or 'list-unsubscribe' in frontmatter:
            return 'mailing_list'
        elif len(frontmatter.get('to', [])) > 1:
            return 'group'
        elif len(frontmatter.get('to', [])) == 1:
            return 'direct'
        else:
            return 'unknown'
    
    def calculate_score(self, email_data):
        """Calculate a score to help determine the email's value."""
        score = 0
        
        # Type weight
        email_type = email_data['email_type']
        score += self.config['type_weights'].get(email_type, 0)
        
        # Age factors
        age = email_data['age_days']
        if age is not None:
            if age <= self.config['recent_threshold_days']:
                score += 2  # Recent emails are more valuable
            elif age >= self.config['old_threshold_days']:
                score -= 1  # Old emails are less valuable
        
        # Size factors
        body_length = email_data['body_length']
        if body_length <= self.config['small_email_threshold']:
            score -= 1  # Very short emails are less valuable
        elif body_length >= self.config['large_email_threshold']:
            score += 1  # Long emails might be more valuable
        
        # Attachment factors
        if email_data['has_attachments']:
            if self.config['keep_with_attachments']:
                score += 2  # Emails with attachments are more valuable
            else:
                score -= 1  # Emails with attachments are less valuable
        
        # Subject analysis
        subject = email_data['subject'].lower()
        
        # Check for delete keywords in subject
        delete_keywords_found = sum(1 for keyword in self.config['delete_keywords'] 
                                   if keyword in subject)
        score -= delete_keywords_found
        
        # Check for keep keywords in subject
        keep_keywords_found = sum(1 for keyword in self.config['keep_keywords'] 
                                 if keyword in subject)
        score += keep_keywords_found * 2
        
        # Sender analysis
        sender = email_data['sender'].lower()
        
        # Check if sender is in delete list
        if any(domain in sender for domain in self.config['delete_senders']):
            score -= 3
        
        # Check if sender is in keep list
        if any(domain in sender for domain in self.config['keep_senders']):
            score += 3
        
        # Body content analysis
        body = email_data['body'].lower()
        
        # Check for important content in body
        important_content = any(keyword in body for keyword in [
            'contract', 'invoice', 'legal', 'urgent', 'important', 
            'confidential', 'agreement', 'signature', 'payment'
        ])
        
        if important_content:
            score += 2
        
        return score
    
    def determine_category(self, email_data):
        """Determine the category based on the email data and score."""
        score = email_data['score']
        
        # Check whitelist first - if sender is whitelisted, always keep
        sender_email = email_data['sender'].lower()
        if self.is_whitelisted(sender_email):
            return 'keep'
        
        # Strong delete indicators
        delete_indicators = [
            email_data['email_type'] == 'newsletter',
            any(keyword in email_data['subject'].lower() 
                for keyword in self.config['delete_keywords']),
            any(sender in email_data['sender'].lower() 
                for sender in self.config['delete_senders'])
        ]
        
        # Strong keep indicators
        keep_indicators = [
            any(keyword in email_data['subject'].lower() 
                for keyword in self.config['keep_keywords']),
            any(sender in email_data['sender'].lower() 
                for sender in self.config['keep_senders']),
            email_data['has_attachments'] and self.config['keep_with_attachments'],
            any(keyword in email_data['body'].lower() 
                for keyword in ['contract', 'invoice', 'legal', 'urgent', 'important'])
        ]
        
        # Apply rules
        if any(keep_indicators):
            return 'keep'
        elif any(delete_indicators) or score <= -2:
            return 'delete'
        elif score >= 2 or email_data['body_length'] > self.config['summarize_max_length']:
            return 'keep'
        else:
            return 'summarize'
    
    def sort_emails(self):
        """Main method to sort all emails in the directory."""
        print(f"🔍 Sorting emails in: {self.base_directory}")
        
        # Walk through the directory structure
        for root, dirs, files in os.walk(self.base_directory):
            # Skip attachment directories
            if 'attachments' in root:
                continue
                
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    email_data = self.analyze_email_file(file_path)
                    
                    if email_data:
                        self.stats['total_emails'] += 1
                        category = email_data['category']
                        self.categories[category].append(email_data)
                        self.stats['by_category'][category] += 1
                        
                        # Update statistics
                        self.stats['by_type'][email_data['email_type']] += 1
                        self.stats['by_sender'][email_data['sender']] += 1
                        
                        if email_data['date']:
                            date_key = email_data['date'].strftime('%Y-%m')
                            self.stats['by_date'][date_key] += 1
        
        return self.categories
    
    def generate_report(self):
        """Generate a report of the sorting results."""
        report = {
            'summary': {
                'total_emails': self.stats['total_emails'],
                'categories': self.stats['by_category'],
                'recommendations': {}
            },
            'details': {
                'by_type': dict(self.stats['by_type']),
                'by_sender': dict(self.stats['by_sender'].most_common(10)),
                'by_date': dict(self.stats['by_date'])
            },
            'categories': {}
        }
        
        # Generate recommendations
        total = self.stats['total_emails']
        if total > 0:
            delete_pct = (self.stats['by_category']['delete'] / total) * 100
            summarize_pct = (self.stats['by_category']['summarize'] / total) * 100
            keep_pct = (self.stats['by_category']['keep'] / total) * 100
            
            report['summary']['recommendations'] = {
                'delete': f"{delete_pct:.1f}% of emails can be deleted",
                'summarize': f"{summarize_pct:.1f}% of emails can be summarized",
                'keep': f"{keep_pct:.1f}% of emails should be kept in full"
            }
        
        # Add category details
        for category, emails in self.categories.items():
            report['categories'][category] = [
                {
                    'file': os.path.relpath(email['file_path'], self.base_directory),
                    'subject': email['subject'],
                    'sender': email['sender'],
                    'date': email['date'].strftime('%Y-%m-%d') if email['date'] else 'Unknown',
                    'score': email['score'],
                    'type': email['email_type'],
                    'size': email['file_size'],
                    'attachments': email['attachment_count']
                }
                for email in emails
            ]
        
        return report
    
    def save_report(self, report, output_file='sort_report.json'):
        """Save the sorting report to a file."""
        output_path = os.path.join(self.base_directory, output_file)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Report saved to: {output_path}")
        return output_path
    
    def print_summary(self):
        """Print a summary of the sorting results."""
        print("\n" + "="*50)
        print("📈 EMAIL SORTING SUMMARY")
        print("="*50)
        
        print(f"📧 Total emails analyzed: {self.stats['total_emails']}")
        print(f"🗑️  To delete: {self.stats['by_category']['delete']}")
        print(f"📝 To summarize: {self.stats['by_category']['summarize']}")
        print(f"💾 To keep: {self.stats['by_category']['keep']}")
        
        if self.stats['total_emails'] > 0:
            delete_pct = (self.stats['by_category']['delete'] / self.stats['total_emails']) * 100
            summarize_pct = (self.stats['by_category']['summarize'] / self.stats['total_emails']) * 100
            keep_pct = (self.stats['by_category']['keep'] / self.stats['total_emails']) * 100
            
            print(f"\n📊 Percentages:")
            print(f"   Delete: {delete_pct:.1f}%")
            print(f"   Summarize: {summarize_pct:.1f}%")
            print(f"   Keep: {keep_pct:.1f}%")
        
        print(f"\n📁 Email types found:")
        for email_type, count in self.stats['by_type'].most_common():
            print(f"   {email_type}: {count}")
        
        print(f"\n👥 Top senders:")
        for sender, count in self.stats['by_sender'].most_common(5):
            print(f"   {sender}: {count}")
        
        print("="*50)

def load_accounts_config():
    """Load accounts configuration from accounts.yaml"""
    try:
        with open('../config/accounts.yaml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("⚠️  accounts.yaml not found - using manual directory specification")
        return None
    except Exception as e:
        print(f"⚠️  Could not load accounts.yaml: {e}")
        return None

def list_accounts_from_config():
    """List available accounts from accounts.yaml"""
    config = load_accounts_config()
    if not config or 'accounts' not in config:
        return []
    
    return config['accounts']

def get_account_export_directory(account_name):
    """Get export directory for a specific account"""
    accounts = list_accounts_from_config()
    
    for account in accounts:
        if account['name'].lower() == account_name.lower():
            return account.get('export_directory', None)
    
    return None

def main():
    """Main function to run the email sorter."""
    parser = argparse.ArgumentParser(description='Sort email markdown files into categories')
    parser.add_argument('directory', help='Directory containing email markdown files', nargs='?')
    parser.add_argument('--config', help='Config file for sorting rules', default=None)
    parser.add_argument('--report', help='Output report file name', default='sort_report.json')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    parser.add_argument('--create-config', help='Create a default configuration file', 
                       action='store_true')
    parser.add_argument('--account', help='Sort emails for a specific account from accounts.yaml')
    parser.add_argument('--list-accounts', help='List available accounts from accounts.yaml', 
                       action='store_true')
    parser.add_argument('--dry-run', help='Simulate sorting without creating reports (safe preview)', 
                       action='store_true')
    
    args = parser.parse_args()
    
    # Handle --create-config option
    if args.create_config:
        if args.directory:
            config_path = args.directory
        else:
            config_path = '../config/sort_config.json'
        
        create_default_config(config_path)
        print(f"📝 Configuration file created: {config_path}")
        return
    
    # Handle --list-accounts option
    if args.list_accounts:
        accounts = list_accounts_from_config()
        if accounts:
            print("📋 Available accounts from accounts.yaml:")
            for i, account in enumerate(accounts, 1):
                export_dir = account.get('export_directory', 'Not configured')
                print(f"   {i}. {account['name']} → {export_dir}")
        else:
            print("❌ No accounts found in accounts.yaml")
        return
    
    # Determine directory to sort
    sort_directory = None
    
    if args.account:
        # Use account from accounts.yaml
        sort_directory = get_account_export_directory(args.account)
        if not sort_directory:
            print(f"❌ Account '{args.account}' not found in accounts.yaml")
            print("   Available accounts:")
            accounts = list_accounts_from_config()
            for account in accounts:
                print(f"   - {account['name']}")
            sys.exit(1)
        
        print(f"🎯 Sorting emails for account: {args.account}")
        print(f"   Directory: {sort_directory}")
    elif args.directory:
        # Use manually specified directory
        sort_directory = args.directory
    else:
        # Try to find a default account or show error
        accounts = list_accounts_from_config()
        if accounts:
            print("📋 Available accounts (use --account NAME or specify directory):")
            for account in accounts:
                print(f"   - {account['name']}")
            print("\nUsage examples:")
            print(f"   python3 {sys.argv[0]} --account Gmail")
            print(f"   python3 {sys.argv[0]} /path/to/emails")
        else:
            parser.print_help()
            print("\n❌ Error: No directory specified and no accounts.yaml found")
            print("   Options:")
            print("   1. Specify a directory directly")
            print("   2. Use --account with a configured account")
            print("   3. Create accounts.yaml with email export configuration")
        sys.exit(1)
    
    # Create sorter instance
    sorter = EmailSorter(sort_directory, args.config)
    
    # Sort emails
    if args.dry_run:
        print("🔍 DRY RUN MODE: Analyzing emails without creating reports")
        print("   This is a safe preview - no files will be modified")
        print()
    
    categories = sorter.sort_emails()
    
    # Generate and save report
    report = sorter.generate_report()
    
    if not args.dry_run:
        sorter.save_report(report, args.report)
    else:
        print(f"📊 DRY RUN: Would create report at: {os.path.join(sorter.base_directory, args.report)}")
    
    # Print summary
    sorter.print_summary()
    
    if args.dry_run:
        print("\n🔒 DRY RUN COMPLETE")
        print("   No files were modified. To apply these changes, run without --dry-run")
        print(f"   Command: python3 {sys.argv[0]} {' '.join([arg for arg in sys.argv[1:] if arg != '--dry-run'])}")
    
    if args.verbose:
        print("\n📋 DETAILED RESULTS:")
        for category, emails in categories.items():
            print(f"\n{category.upper()} ({len(emails)} emails):")
            for email in emails[:5]:  # Show first 5 of each category
                print(f"  • {email['subject']} (from: {email['sender']}, score: {email['score']})")
            if len(emails) > 5:
                print(f"  ... and {len(emails) - 5} more")

def create_default_config(output_path='../config/sort_config.json'):
    """Create a default configuration file with whitelist support."""
    default_config = {
        "delete_keywords": [
            "newsletter", "bulletin", "digest", "promotion", "offer",
            "coupon", "sale", "unsubscribe", "marketing", "advertisement",
            "publicité", "promo", "réduction", "soldes", "abonnements"
        ],
        "delete_senders": [
            "newsletter@", "no-reply@", "marketing@", "promo@", "info@"
        ],
        "delete_subjects": [
            "Your weekly digest", "Monthly newsletter", "Special offer",
            "Limited time offer", "Weekly update", "Newsletter"
        ],
        
        "summarize_keywords": [
            "meeting", "update", "status", "report", "follow-up",
            "réunion", "mise à jour", "statut", "rapport", "suivi"
        ],
        
        "keep_keywords": [
            "contract", "invoice", "legal", "urgent", "important", "confidential",
            "agreement", "signature", "payment", "facture", "contrat",
            "paiement", "urgent", "important", "confidentiel", "signature"
        ],
        "keep_senders": [
            "contracts@", "billing@", "legal@", "facture@", "paiement@"
        ],
        "keep_subjects": [
            "Contract", "Invoice", "Legal Notice", "Payment Confirmation",
            "Contrat", "Facture", "Avis légal", "Confirmation de paiement"
        ],
        
        # Whitelist feature - NEW!
        "whitelist": [
            # Add email addresses or domains here to keep ALL emails from these senders
            # Examples:
            # "important-client@example.com",  # Specific email address
            # "@important-domain.com",       # All emails from this domain
            # "boss@"                         # All emails from addresses starting with boss@
        ],
        
        "recent_threshold_days": 30,
        "old_threshold_days": 365,
        
        "small_email_threshold": 500,
        "large_email_threshold": 10000,
        
        "keep_with_attachments": True,
        
        "type_weights": {
            "newsletter": -2,
            "mailing_list": -1,
            "group": 0,
            "direct": 1,
            "unknown": 0
        }
    }
    
    # Add comments to the JSON file for better readability
    config_with_comments = {
        "// WHITELIST SECTION": "// Add users whose emails you always want to keep",
        "whitelist": default_config["whitelist"],
        "// DELETE CRITERIA": "// Criteria for identifying low-value emails",
        "delete_keywords": default_config["delete_keywords"],
        "delete_senders": default_config["delete_senders"],
        "delete_subjects": default_config["delete_subjects"],
        "// KEEP CRITERIA": "// Criteria for identifying important emails",
        "keep_keywords": default_config["keep_keywords"],
        "keep_senders": default_config["keep_senders"],
        "keep_subjects": default_config["keep_subjects"],
        "// THRESHOLDS": "// Configuration for age and size thresholds",
        "recent_threshold_days": default_config["recent_threshold_days"],
        "old_threshold_days": default_config["old_threshold_days"],
        "small_email_threshold": default_config["small_email_threshold"],
        "large_email_threshold": default_config["large_email_threshold"],
        "// ATTACHMENTS": "// How to handle emails with attachments",
        "keep_with_attachments": default_config["keep_with_attachments"],
        "// WEIGHTS": "// Scoring system for different email types",
        "type_weights": default_config["type_weights"]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config_with_comments, f, indent=2, ensure_ascii=False)
    
    # Also create a README for the config file
    readme_content = """# Email Sorting Configuration

This file configures how the email sorting tool categorizes your emails.

## Whitelist Feature (NEW!)

The whitelist allows you to specify users whose emails should ALWAYS be kept,
regardless of other sorting criteria.

### How to use the whitelist:

1. **Specific email addresses**: Add full email addresses
   ```json
   "whitelist": ["important@client.com", "boss@company.com"]
   ```

2. **Entire domains**: Add domains starting with @
   ```json
   "whitelist": ["@important-client.com", "@company.com"]
   ```

3. **Email prefixes**: Add prefixes ending with @
   ```json
   "whitelist": ["ceo@", "director@"]
   ```

### Examples:
- `"john.doe@company.com"` - Keep all emails from this specific address
- `"@company.com"` - Keep all emails from this domain
- `"executive@"` - Keep all emails from addresses starting with executive@

## Configuration Sections

### Delete Criteria
Emails matching these criteria are more likely to be deleted:
- `delete_keywords`: Words in subject that indicate low-value emails
- `delete_senders`: Sender domains/addresses to prioritize for deletion
- `delete_subjects`: Specific subject lines that indicate low-value emails

### Keep Criteria
Emails matching these criteria are more likely to be kept:
- `keep_keywords`: Words in subject that indicate important emails
- `keep_senders`: Sender domains/addresses to prioritize for keeping
- `keep_subjects`: Specific subject lines that indicate important emails

### Thresholds
- `recent_threshold_days`: Emails newer than this get bonus points
- `old_threshold_days`: Emails older than this get penalty points
- `small_email_threshold`: Very short emails get penalty points
- `large_email_threshold`: Very long emails get bonus points

### Attachments
- `keep_with_attachments`: Whether to keep emails that have attachments

### Type Weights
Different email types get different base scores:
- `newsletter`: -2 (likely to delete)
- `mailing_list`: -1 (somewhat likely to delete)
- `group`: 0 (neutral)
- `direct`: 1 (likely to keep)
- `unknown`: 0 (neutral)

## Customization Tips

1. **Start conservative**: Begin with strict keep criteria and loose delete criteria
2. **Review results**: Check the verbose output to see what gets categorized where
3. **Adjust gradually**: Modify the configuration based on the actual sorting results
4. **Use whitelist**: Add important contacts to the whitelist to ensure they're never deleted
"""
    
    readme_path = output_path.replace('.json', '_README.md')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

if __name__ == '__main__':
    main()