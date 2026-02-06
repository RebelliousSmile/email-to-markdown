# Email Export & Sorting Integration Guide

This guide explains how the email export and sorting tools work together seamlessly.

## 🔄 Integrated Workflow

The two scripts now share the same configuration and work together:

```bash
# 1. Export emails from IMAP
EXPORT_SPECIFIC_ACCOUNTS="Gmail" python3 export_emails.py

# 2. Sort the exported emails
python3 sort_emails.py --account Gmail

# 3. Review the results
cat /path/to/export/Gmail/sort_report.json
```

## 📋 New Features

### 1. **Account-Based Sorting** ✅

```bash
# Sort emails for a specific account
python3 sort_emails.py --account Gmail
python3 sort_emails.py --account LaContreVoie
```

**Benefits:**
- Automatically uses the correct export directory from `accounts.yaml`
- Ensures consistency between export and sorting
- No need to manually specify paths

### 2. **Account Listing** ✅

```bash
# List all configured accounts
python3 sort_emails.py --list-accounts
```

Example output:
```
📋 Available accounts from accounts.yaml:
   1. Gmail → /home/tnn/Documents/Emails/Gmail
   2. LaContreVoie → /home/tnn/Documents/Emails/LaContreVoie
```

### 3. **Configuration Creation** ✅

```bash
# Create a default sorting configuration
python3 sort_emails.py --create-config

# Create config with custom name
python3 sort_emails.py --create-config my_config.json
```

### 4. **Whitelist Feature** ✅

```json
{
  "whitelist": [
    "boss@company.com",      // Specific email address
    "@important-client.com", // Entire domain
    "executive@"             // Email prefix
  ]
}
```

**How it works:**
- Emails from whitelisted senders are **ALWAYS kept**
- Overrides all other sorting rules
- Supports flexible matching patterns

## 🎯 Usage Examples

### Basic Workflow

```bash
# Export emails
EXPORT_SPECIFIC_ACCOUNTS="Gmail" python3 export_emails.py

# Sort the exported emails
python3 sort_emails.py --account Gmail

# View results
python3 sort_emails.py --account Gmail --verbose
```

### Multi-Account Workflow

```bash
# Process multiple accounts
for account in Gmail LaContreVoie; do
    echo "Processing $account..."
    python3 sort_emails.py --account "$account"
done
```

### Custom Configuration

```bash
# Create and customize config
python3 sort_emails.py --create-config
nano sort_config.json  # Add your whitelist entries

# Use custom config
python3 sort_emails.py --account Gmail --config sort_config.json
```

## 🔧 Configuration Integration

### accounts.yaml

The sorting tool reads from the same `accounts.yaml` file used by the export tool:

```yaml
accounts:
  - name: "Gmail"
    server: "imap.gmail.com"
    port: 993
    username: "your.email@gmail.com"
    export_directory: "/path/to/export/Gmail"  # ← Used by both tools
    # ... other settings
```

### sort_config.json

Custom sorting rules with whitelist support:

```json
{
  "whitelist": ["boss@company.com", "@important-client.com"],
  "delete_keywords": ["newsletter", "promotion"],
  "keep_keywords": ["contract", "urgent"],
  // ... other settings
}
```

## 📊 Reporting

Both tools generate comprehensive reports:

- **Export tool**: Creates email markdown files with metadata
- **Sorting tool**: Creates JSON reports with categorization

```bash
# View sorting report
cat /path/to/export/Gmail/sort_report.json | jq '.summary'

# Get detailed statistics
cat /path/to/export/Gmail/sort_report.json | jq '.categories.keep[] | .subject'
```

## 🛡️ Safety Features

### 1. Whitelist Protection
- Important contacts are never accidentally deleted
- Domain-level protection (e.g., `@company.com`)
- Email prefix protection (e.g., `executive@`)

### 2. Error Handling
- Graceful handling of malformed email files
- Detailed error messages for debugging
- Continues processing even with errors

### 3. Dry Run Mode
```bash
# Preview what would be sorted (no changes made)
python3 sort_emails.py --account Gmail --verbose
```

## 🔄 Complete Workflow Example

```bash
# 1. Export emails from all accounts
python3 export_emails.py

# 2. List available accounts
python3 sort_emails.py --list-accounts

# 3. Create custom sorting config
python3 sort_emails.py --create-config
nano sort_config.json  # Add whitelist entries

# 4. Sort each account
for account in Gmail LaContreVoie; do
    echo "📊 Sorting $account emails..."
    python3 sort_emails.py --account "$account" --config sort_config.json
    echo "✅ Report saved to: /path/to/export/$account/sort_report.json"
done

# 5. Review results
cat /path/to/export/Gmail/sort_report.json | jq '.summary.categories'
```

## 🎨 Advanced Usage

### Custom Sorting Rules

```bash
# Create aggressive sorting config
cat > aggressive_config.json << 'EOF'
{
  "whitelist": ["boss@company.com"],
  "delete_keywords": ["newsletter", "promotion", "update", "report"],
  "keep_keywords": ["contract", "invoice", "urgent"],
  "recent_threshold_days": 7,
  "old_threshold_days": 180
}
EOF

# Apply aggressive sorting
python3 sort_emails.py --account Gmail --config aggressive_config.json
```

### Batch Processing

```bash
# Process all accounts with same config
for account in $(python3 sort_emails.py --list-accounts 2>/dev/null | grep -oP '(?<=→ ).*'); do
    python3 sort_emails.py --account "$account" --config conservative_config.json
done
```

### Integration with Other Tools

```bash
# Convert report to CSV
jq -r '.categories.delete[] | [.file, .subject, .sender] | @csv' sort_report.json > to_delete.csv

# Get statistics
jq '.summary' sort_report.json
```

## 🚀 Best Practices

### 1. Start Conservative
```json
// Begin with strict keep criteria
"keep_keywords": ["contract", "invoice", "legal", "urgent"],
"whitelist": ["boss@company.com", "@important-client.com"]
```

### 2. Review Before Deleting
```bash
# Always check verbose output first
python3 sort_emails.py --account Gmail --verbose
```

### 3. Use Whitelist Liberally
```json
// Add all important contacts to whitelist
"whitelist": [
  "ceo@company.com",
  "cto@company.com",
  "@key-client.com",
  "@legal-team.com"
]
```

### 4. Regular Maintenance
```bash
# Monthly cleanup workflow
python3 export_emails.py
python3 sort_emails.py --account Gmail --config monthly_cleanup.json
```

## 🔍 Troubleshooting

### Common Issues

**No accounts found:**
- Ensure `accounts.yaml` exists and is properly formatted
- Check that accounts have `export_directory` configured

**Directory not found:**
- Verify the account name matches exactly (case-insensitive)
- Check that the export directory exists

**Parsing errors:**
- Some email files may have formatting issues
- The script continues processing other files
- Use `--verbose` to see which files have issues

### Debugging

```bash
# Verbose output shows detailed processing
python3 sort_emails.py --account Gmail --verbose

# Check accounts.yaml syntax
python3 -c "import yaml; print(yaml.safe_load(open('accounts.yaml')))"
```

## 📚 File Structure

```
project/
├── export_emails.py          # Email export tool
├── sort_emails.py            # Email sorting tool (NEW!)
├── accounts.yaml            # Shared configuration
├── sort_config.json         # Sorting rules
├── sort_config_README.md    # Configuration documentation
├── emails/
│   ├── Gmail/               # Export directory
│   │   ├── INBOX/           # Email folders
│   │   ├── sort_report.json # Sorting report
│   │   └── ...
│   └── LaContreVoie/        # Another account
│       ├── INBOX/           # Email folders
│       ├── sort_report.json # Sorting report
│       └── ...
└── ...
```

## 🎯 Summary

The integrated system provides:

1. **Seamless workflow**: Export → Sort → Review
2. **Consistent configuration**: Both tools use `accounts.yaml`
3. **Powerful sorting**: Whitelist, keywords, scoring system
4. **Comprehensive reporting**: Detailed statistics and analysis
5. **Safety features**: Whitelist protection, error handling

This creates a complete email management solution from IMAP to organized archives!