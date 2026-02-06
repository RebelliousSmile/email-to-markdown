# Dry Run Mode Guide

## 🛡️ Safety First: Dry Run Mode

The dry-run mode allows you to preview email sorting results **without making any changes**. This is essential for safety when dealing with important email archives.

## 🎯 What Dry Run Does

- **Analyzes** all emails and determines categorization
- **Shows** detailed statistics and preview
- **Does NOT create** any report files
- **Does NOT modify** any existing files
- **Provides** the exact command to run for real execution

## 📖 Usage

### Basic Dry Run

```bash
# Preview sorting for an account
python3 sort_emails.py --account Gmail --dry-run

# Preview sorting for a directory
python3 sort_emails.py /path/to/emails --dry-run
```

### Dry Run with Custom Configuration

```bash
# Preview with custom sorting rules
python3 sort_emails.py --account Gmail --config aggressive_config.json --dry-run
```

### Dry Run with Verbose Output

```bash
# Get detailed preview of what would be sorted
python3 sort_emails.py --account Gmail --dry-run --verbose
```

## 🔍 Example Workflow

### Safe Email Management Process

```bash
# 1. Export emails
python3 export_emails.py --account Gmail

# 2. Preview sorting (DRY RUN - SAFE)
python3 sort_emails.py --account Gmail --dry-run --verbose

# 3. Review the results carefully
#    - Check percentages
#    - Verify whitelist is working
#    - Confirm important emails are in "keep" category

# 4. Apply sorting (only if preview looks good)
python3 sort_emails.py --account Gmail
```

### Multi-Account Safety Check

```bash
# Check all accounts before processing
for account in Gmail LaContreVoie; do
    echo "🔍 Previewing $account..."
    python3 sort_emails.py --account "$account" --dry-run
    echo "✅ Preview complete - review results above"
    read -p "Press Enter to continue..." 
done

# After reviewing, apply to all accounts
for account in Gmail LaContreVoie; do
    python3 sort_emails.py --account "$account"
done
```

## 📊 Dry Run Output Example

```
🔍 DRY RUN MODE: Analyzing emails without creating reports
   This is a safe preview - no files will be modified

🔍 Sorting emails in: /home/tnn/Documents/Emails/Gmail
📊 DRY RUN: Would create report at: /home/tnn/Documents/Emails/Gmail/sort_report.json

==================================================
📈 EMAIL SORTING SUMMARY
==================================================
📧 Total emails analyzed: 1507
🗑️  To delete: 11 (0.7%)
📝 To summarize: 418 (27.7%)
💾 To keep: 1078 (71.5%)

📊 Percentages:
   Delete: 0.7%
   Summarize: 27.7%
   Keep: 71.5%

📁 Email types found:
   group: 1506
   newsletter: 1

👥 Top senders:
   David Espic <ed@smartlockers.io>: 260
   François-Xavier Guillois <pro@fxguillois.email>: 81
   Firat Yildirim <fy@smartlockers.io>: 68

🔒 DRY RUN COMPLETE
   No files were modified. To apply these changes, run without --dry-run
   Command: python3 sort_emails.py --account Gmail
```

## 🎨 Advanced Dry Run Techniques

### Compare Different Configurations

```bash
# Create different config files
python3 sort_emails.py --create-config conservative_config.json
python3 sort_emails.py --create-config aggressive_config.json

# Edit the configs with different rules
nano conservative_config.json  # Strict: keep more emails
nano aggressive_config.json    # Loose: delete more emails

# Compare results
echo "📊 Conservative approach:"
python3 sort_emails.py --account Gmail --config conservative_config.json --dry-run

echo "\n📊 Aggressive approach:"
python3 sort_emails.py --account Gmail --config aggressive_config.json --dry-run
```

### Test Whitelist Effectiveness

```bash
# Test without whitelist
python3 sort_emails.py --account Gmail --dry-run

# Add important contacts to whitelist
nano sort_config.json

# Test with whitelist
python3 sort_emails.py --account Gmail --config sort_config.json --dry-run

# Compare the "keep" percentages
```

### Batch Preview for Multiple Accounts

```bash
# Preview all accounts
for account in $(python3 sort_emails.py --list-accounts 2>/dev/null | grep -oP '(?<=\d\. ).*?(?= →)'); do
    echo "=== DRY RUN: $account ==="
    python3 sort_emails.py --account "$account" --dry-run
    echo ""
done
```

## 🚀 Best Practices

### 1. Always Dry Run First

**Before any real sorting operation, always run a dry run:**

```bash
# ❌ DON'T do this (risky)
python3 sort_emails.py --account Gmail

# ✅ DO this (safe)
python3 sort_emails.py --account Gmail --dry-run
# Review results, then run without --dry-run
```

### 2. Check Critical Metrics

**Before applying sorting, verify:**

- **Delete percentage**: Should be low (<5% for most users)
- **Whitelist effectiveness**: Important contacts should be in "keep"
- **Attachment handling**: Emails with attachments should be kept
- **Recent emails**: Should mostly be in "keep" or "summarize"

### 3. Start Conservative

**Begin with strict keep criteria:**

```json
{
  "whitelist": ["boss@company.com", "@important-client.com"],
  "keep_keywords": ["contract", "invoice", "legal", "urgent"],
  "delete_keywords": ["newsletter"]  // Start with few delete keywords
}
```

### 4. Gradually Adjust Rules

**Refine configuration based on dry run results:**

```bash
# Run dry run
python3 sort_emails.py --account Gmail --dry-run --verbose

# Adjust configuration
nano sort_config.json

# Test again
python3 sort_emails.py --account Gmail --dry-run

# Repeat until satisfied
```

### 5. Use Verbose Mode for Dry Runs

**Always use `--verbose` with dry runs to see details:**

```bash
python3 sort_emails.py --account Gmail --dry-run --verbose
```

## 🛡️ Safety Checklist

**Before applying sorting (remove --dry-run):**

- [ ] ✅ Dry run shows reasonable delete percentage (<5%)
- [ ] ✅ Important contacts are in "keep" category
- [ ] ✅ Whitelist is properly configured
- [ ] ✅ Recent important emails are not marked for deletion
- [ ] ✅ Emails with attachments are preserved
- [ ] ✅ Reviewed verbose output for any surprises
- [ ] ✅ Backed up email directory (optional but recommended)

## 🔧 Technical Details

### How Dry Run Works

1. **Analyzes emails**: Reads and categorizes all email files
2. **Calculates statistics**: Computes percentages and metrics
3. **Generates report in memory**: Creates report but doesn't save to disk
4. **Shows preview**: Displays what would happen
5. **Provides command**: Shows exact command to run for real execution

### What Dry Run Does NOT Do

- Does not create `sort_report.json` file
- Does not modify any email files
- Does not change any directory structure
- Does not affect original emails in any way

### Performance Impact

- **Same analysis speed**: Dry run is as fast as real sorting
- **No disk I/O for reports**: Slightly faster than real run
- **Memory usage**: Same as real sorting (report stored in memory)

## 🎯 Real-World Examples

### Example 1: Conservative Cleanup

```bash
# Create conservative config
python3 sort_emails.py --create-config

# Edit to keep almost everything
nano sort_config.json

# Preview
python3 sort_emails.py --account Gmail --dry-run

# Apply if results look good
python3 sort_emails.py --account Gmail
```

### Example 2: Aggressive Cleanup

```bash
# Create aggressive config
cat > aggressive_config.json << 'EOF'
{
  "whitelist": ["boss@company.com"],
  "delete_keywords": ["newsletter", "promotion", "update", "report", "digest"],
  "keep_keywords": ["contract", "invoice", "urgent"],
  "old_threshold_days": 180
}
EOF

# Preview aggressive cleanup
python3 sort_emails.py --account Gmail --config aggressive_config.json --dry-run

# Only apply if you're sure!
```

### Example 3: Whitelist Testing

```bash
# Test current config
python3 sort_emails.py --account Gmail --dry-run

# Add to whitelist
nano sort_config.json

# Test with updated whitelist
python3 sort_emails.py --account Gmail --config sort_config.json --dry-run

# Compare results
```

## 🚨 Common Pitfalls & Solutions

### Pitfall 1: Too Many Emails Marked for Deletion

**Problem:** Dry run shows 30%+ emails would be deleted

**Solution:**
```bash
# Make keep criteria more inclusive
nano sort_config.json
# Add more keep_keywords
# Reduce delete_keywords
# Add more entries to whitelist
```

### Pitfall 2: Important Emails in Delete Category

**Problem:** Critical emails are marked for deletion

**Solution:**
```bash
# Add senders to whitelist
nano sort_config.json
# Add specific email addresses or domains to whitelist
```

### Pitfall 3: Newsletters in Keep Category

**Problem:** Obvious spam/newsletters are marked to keep

**Solution:**
```bash
# Add newsletter keywords to delete_keywords
nano sort_config.json
# Add: "newsletter", "bulletin", "digest", "unsubscribe"
```

## 📚 Summary

The dry-run mode is your **safety net** for email sorting. It provides:

1. **Risk-free preview** of sorting results
2. **Confidence building** before applying changes
3. **Configuration testing** without consequences
4. **Whitelist verification**
5. **Statistical analysis** before commitment

**Golden Rule:** Always run with `--dry-run` first, review carefully, then apply!

```bash
# Safe workflow
python3 sort_emails.py --account Gmail --dry-run --verbose
# Review results...
python3 sort_emails.py --account Gmail  # Only if satisfied
```

This ensures you never accidentally lose important emails while still benefiting from automated categorization!