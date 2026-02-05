import imaplib
import email
import os
import re
import yaml
import hashlib
import fnmatch
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load account configuration from YAML file
with open('accounts.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Inject passwords from .env
for account in config['accounts']:
    # Try APPLICATION_PASSWORD first (for Gmail 2FA), then fall back to PASSWORD
    password_var = f"{account['name'].upper()}_APPLICATION_PASSWORD"
    account['password'] = os.getenv(password_var) or os.getenv(f"{account['name'].upper()}_PASSWORD")

def limit_quote_depth(text, max_depth):
    """Limit the depth of quoted messages to reduce redundancy."""
    lines = text.split('\n')
    quote_stack = []
    result_lines = []
    
    for line in lines:
        # Count leading '>' characters to determine quote depth
        quote_level = 0
        while quote_level < len(line) and line[quote_level] == '>':
            quote_level += 1
        
        # If quote level exceeds max depth, skip the line
        if quote_level > max_depth:
            continue
            
        result_lines.append(line)
    
    return '\n'.join(result_lines)

def email_already_exported(email_message, export_directory):
    """Check if an email has already been exported by looking for existing files."""
    # Generate the expected filename pattern
    date_obj = email.utils.parsedate_to_datetime(email_message["Date"])
    if not date_obj:
        return False
    
    date_str = date_obj.strftime("%Y-%m-%d")
    
    def get_short_name(email_str):
        # Same logic as in export_to_markdown
        clean = email_str.replace("<", "").replace(">", "")
        if "@" in clean:
            name_part = clean.split("@")[0]
        else:
            name_part = clean
        words = name_part.split()
        if len(words) == 1:
            short_name = words[0][:3].upper()
        else:
            short_name = ''.join(word[0].upper() for word in words[:3])
        short_name = re.sub(r'[^A-Z]', '', short_name)
        return short_name if short_name else "UNK"
    
    sender_short = get_short_name(email_message["From"])
    recipient_short = get_short_name(email_message["To"])
    
    # Look for existing files with this pattern
    search_pattern = f"email_{date_str}_{sender_short}_to_{recipient_short}*.md"
    existing_files = []
    
    if os.path.exists(export_directory):
        for filename in os.listdir(export_directory):
            if fnmatch.fnmatch(filename, search_pattern):
                existing_files.append(filename)
    
    return len(existing_files) > 0

def export_to_markdown(raw_email, export_directory, base_export_directory, num, tags, quote_depth=1, account=None):
    """Export an email to Markdown with frontmatter and handle attachments."""
    email_message = email.message_from_bytes(raw_email)

    # Check if email has already been exported (if skip_existing is enabled)
    if account is None:
        account = {}
    skip_existing = account.get('skip_existing', True)
    if skip_existing and email_already_exported(email_message, export_directory):
        print(f"⏭️  Email already exported, skipping: {email_message['Subject'][:50]}...")
        return False

    frontmatter = {
        "from": email_message["From"],
        "to": email_message["To"],
        "date": email.utils.parsedate_to_datetime(email_message["Date"]).isoformat(),
        "subject": email_message["Subject"],
        "tags": tags,
        "attachments": []
    }

    # Create a descriptive filename
    date_obj = email.utils.parsedate_to_datetime(email_message["Date"])
    date_str = date_obj.strftime("%Y-%m-%d")
    
    # Extract initials or short names for sender and recipient
    def get_short_name(email_str):
        # Remove <> and everything inside
        clean = email_str.replace("<", "").replace(">", "")
        
        # Extract name part (before @ if email, or full name)
        if "@" in clean:
            name_part = clean.split("@")[0]
        else:
            name_part = clean
        
        # Get initials or short name
        words = name_part.split()
        if len(words) == 1:
            # Single word: use first 3 letters
            short_name = words[0][:3].upper()
        else:
            # Multiple words: use first letter of each word (max 3 words)
            short_name = ''.join(word[0].upper() for word in words[:3])
        
        # Clean up any remaining special characters
        short_name = re.sub(r'[^A-Z]', '', short_name)
        
        # Fallback to "UNK" if empty
        return short_name if short_name else "UNK"
    
    sender_short = get_short_name(email_message["From"])
    recipient_short = get_short_name(email_message["To"])
    
    # Create filename: email_YYYY-MM-DD_EFR_to_CAC.md
    filename = f"email_{date_str}_{sender_short}_to_{recipient_short}.md"

    body = ""
    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
            elif content_type == "text/html" and not body:
                body = part.get_payload(decode=True).decode(errors="ignore")
    else:
        body = email_message.get_payload(decode=True).decode(errors="ignore")

    # Process quote depth to reduce redundant content
    if quote_depth > 0:
        body = limit_quote_depth(body, quote_depth)

    # Create attachments directory in the same relative path as the email
    # Get the relative path from the base export directory to current export directory
    relative_path = os.path.relpath(export_directory, base_export_directory)
    
    # Create attachments directory structure
    attachments_base_dir = os.path.join(base_export_directory, "attachments")
    attachments_dir = os.path.join(attachments_base_dir, relative_path)
    os.makedirs(attachments_dir, exist_ok=True)

    # Use a base name for attachments (without .md extension)
    base_filename = filename.replace(".md", "")
    
    for part in email_message.walk():
        if part.get_content_maintype() == 'multipart':
            continue
        if part.get('Content-Disposition') is None:
            continue
        attachment_filename = part.get_filename()
        if attachment_filename:
            filename_hash = hashlib.md5(attachment_filename.encode()).hexdigest()[:8]
            filepath = os.path.join(attachments_dir, f"{base_filename}_{filename_hash}_{attachment_filename}")
            with open(filepath, 'wb') as f:
                f.write(part.get_payload(decode=True))
            # Calculate relative path from base export directory to attachments directory
            relative_attachments_path = os.path.relpath(attachments_dir, base_export_directory)
            frontmatter["attachments"].append(f"{relative_attachments_path}/{base_filename}_{filename_hash}_{attachment_filename}")

    # Normalize line breaks to max 2 consecutive newlines
    def normalize_line_breaks(text):
        # Replace any sequence of 3 or more newlines with exactly 2 newlines
        return re.sub(r'\n{3,}', '\n\n', text)
    
    # Apply normalization to the email body
    normalized_body = normalize_line_breaks(body)
    
    with open(f"{export_directory}/{filename}", "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(frontmatter, f, allow_unicode=True, sort_keys=False)
        f.write("---\n\n")
        f.write(normalized_body)

def export_folder(mail, imap_folder, base_export_directory, delete_after_export=False):
    """Export all emails from an IMAP folder (including nested folders)."""
    status, messages = mail.select(imap_folder)
    if status != "OK":
        print(f"⚠️ Unable to select {imap_folder}")
        return

    status, messages = mail.search(None, "ALL")
    if status != "OK":
        print(f"⚠️ No emails in {imap_folder}")
        return

    export_directory = os.path.join(base_export_directory, *imap_folder.split('/'))
    os.makedirs(export_directory, exist_ok=True)

    for num in messages[0].split():
        status, data = mail.fetch(num, "(RFC822)")
        if status == "OK":
            raw_email = data[0][1]
            quote_depth = account.get('quote_depth', 3)
            export_to_markdown(raw_email, export_directory, account['export_directory'], num, [imap_folder], quote_depth, account)
            if delete_after_export:
                mail.store(num, '+FLAGS', '\\Deleted')

    if delete_after_export:
        mail.expunge()

def export_account(account, delete_after_export=False):
    """Export all emails from an account, handling nested folders."""
    print(f"📧 Processing account: {account['name']} → {account['export_directory']}")
    mail = None
    try:
        mail = imaplib.IMAP4_SSL(account["server"], account["port"])
        mail.login(account["username"], account["password"])

        status, folders = mail.list()
        if status != "OK":
            print("⚠️ Unable to list folders")
            return

        processed_folders = set()  # Track processed folders to avoid duplicates
        
        for folder in folders:
            imap_folder = folder.decode().split('"')[-2]
            
            # Skip invalid folder names and duplicates
            if not imap_folder or imap_folder == "." or imap_folder.startswith(".."):
                continue
            
            if imap_folder in processed_folders:
                continue
                
            processed_folders.add(imap_folder)
            
            if imap_folder in account["ignored_folders"]:
                print(f"🗑️ Ignored folder: {imap_folder}")
                continue

            print(f"📁 Exporting {imap_folder} → {os.path.join(account['export_directory'], *imap_folder.split('/'))}")
            export_folder(mail, imap_folder, account["export_directory"], delete_after_export)

        # Only close if we're in SELECTED state, otherwise just logout
        try:
            mail.close()
        except:
            pass  # Ignore close errors (e.g., not in SELECTED state)
        
        mail.logout()
        print(f"✅ Export completed for {account['name']}\n")

    except Exception as e:
        print(f"❌ Error for {account['name']}: {e}")
        try:
            if mail:
                mail.logout()
        except:
            pass

# Run export for all accounts
for account in config['accounts']:
    export_account(account, delete_after_export=False)
