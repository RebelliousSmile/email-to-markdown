import imaplib
import email
import os
import re
import yaml
import hashlib
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

def export_to_markdown(raw_email, export_directory, num, tags):
    """Export an email to Markdown with frontmatter and handle attachments."""
    email_message = email.message_from_bytes(raw_email)

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
    
    # Extract clean sender and recipient names (remove email addresses and special chars)
    def clean_email_address(email_str):
        # Remove <> and everything inside
        clean = email_str.replace("<", "").replace(">", "")
        # Extract name part before @ if present
        if "@" in clean:
            clean = clean.split("@")[0]
        # Replace special characters and spaces
        clean = clean.replace(" ", "_").replace("@", "_at_").replace(",", "_").replace("=", "").replace("?", "").replace("!", "")
        clean = clean.replace("&", "and").replace("#", "").replace("$", "").replace("%", "")
        # Remove any remaining non-alphanumeric characters
        import re
        clean = re.sub(r'[^\w\-]', '', clean)
        # Limit to reasonable length
        return clean[:50]
    
    sender_clean = clean_email_address(email_message["From"])
    recipient_clean = clean_email_address(email_message["To"])
    
    # Create filename: email_YYYY-MM-DD_from-sender_to-recipient.md
    filename = f"email_{date_str}_from-{sender_clean}_to-{recipient_clean}.md"
    
    # Limit total filename length to avoid filesystem issues
    max_length = 150  # Reduced from 200 to be safer
    if len(filename) > max_length:
        # Keep date and truncate sender/recipient parts
        available_length = max_length - len("email_YYYY-MM-DD_from-_to-_.md")
        sender_part = sender_clean[:available_length//2]
        recipient_part = recipient_clean[:available_length//2]
        filename = f"email_{date_str}_from-{sender_part}_to-{recipient_part}.md"

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

    attachments_dir = os.path.join(export_directory, "attachments")
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
            frontmatter["attachments"].append(f"attachments/{base_filename}_{filename_hash}_{attachment_filename}")

    with open(f"{export_directory}/{filename}", "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(frontmatter, f, allow_unicode=True, sort_keys=False)
        f.write("---\n\n")
        f.write(body)

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
            export_to_markdown(raw_email, export_directory, num, [imap_folder])
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
