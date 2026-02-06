# Email Sorting Configuration

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
