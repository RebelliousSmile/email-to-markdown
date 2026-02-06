import imaplib
import email
import os
import re
import yaml
import hashlib
import fnmatch
import csv
import traceback
import base64
import quopri
import argparse
import sys
from datetime import datetime
from dotenv import load_dotenv
from collections import defaultdict

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

def analyze_email_type(email_message):
    """Analyze email type and extract contact information."""
    email_type = "unknown"
    contacts = set()
    
    # Extract basic information
    from_field = email_message.get("From", "")
    to_field = email_message.get("To", "")
    cc_field = email_message.get("Cc", "")
    subject = email_message.get("Subject", "")
    
    # Clean email addresses
    def extract_emails(text):
        # Extract emails from text like "Name <email@domain.com>" or just "email@domain.com"
        # Handle Header objects by converting to string
        if text is None:
            return []
        text_str = str(text)
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text_str)
        return [e.lower() for e in emails]
    
    from_emails = extract_emails(from_field)
    to_emails = extract_emails(to_field)
    cc_emails = extract_emails(cc_field)
    
    # Determine email type
    if len(to_emails) > 1 or len(cc_emails) > 1:
        email_type = "group"
    elif subject and any(keyword in str(subject).lower() for keyword in ["newsletter", "bulletin", "digest"]):
        email_type = "newsletter"
    elif "list-id" in email_message or "list-unsubscribe" in email_message:
        email_type = "mailing_list"
    elif len(from_emails) == 1 and len(to_emails) == 1:
        email_type = "direct"
    
    # Collect all unique contacts
    all_emails = from_emails + to_emails + cc_emails
    for email_addr in all_emails:
        if email_addr and email_addr != email_message.get("From", ""):
            contacts.add(email_addr)
    
    return {
        "type": email_type,
        "from": from_emails[0] if from_emails else "",
        "to": to_emails,
        "cc": cc_emails,
        "contacts": list(contacts),
        "subject": subject
    }

def email_already_exported(email_message, export_directory):
    """Check if an email has already been exported by looking for existing files."""
    # Generate the expected filename pattern
    date_obj = email.utils.parsedate_to_datetime(email_message["Date"])
    if not date_obj:
        return False
    
    date_str = date_obj.strftime("%Y-%m-%d")
    
    def get_short_name(email_str):
        # Same logic as in export_to_markdown
        # Handle None values
        if email_str is None:
            return "UNK"
        
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
    
    # If we found existing files, check if this specific email (with same subject) already exists
    if existing_files:
        # Get the subject hash to make it more unique
        subject = email_message.get("Subject", "")
        if subject:
            # Ensure subject is a string before encoding
            if isinstance(subject, str):
                subject_hash = hashlib.md5(subject.encode()).hexdigest()[:6]
            else:
                # Convert to string if it's not already
                subject_hash = hashlib.md5(str(subject).encode()).hexdigest()[:6]
        else:
            subject_hash = "no-subject"
        
        # Check if any existing file has the same subject hash in its content
        for filename in existing_files:
            filepath = os.path.join(export_directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if subject_hash in content:
                        return True
            except:
                continue
    
    return False

def generate_contacts_file(contacts_data, base_export_directory, account_name):
    """Generate a contacts file compatible with major email clients."""
    # Generate filename with current date
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"contacts_{account_name}_{date_str}.csv"
    filepath = os.path.join(base_export_directory, filename)
    
    # CSV format compatible with Thunderbird, Gmail, Outlook, etc.
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header for CSV
        writer.writerow(["Name", "Email", "Type", "Source", "Notes"])
        
        # Write contacts
        for contact_type, contacts in contacts_data.items():
            for contact in contacts:
                # Extract name from email if possible
                name = contact.split('@')[0].replace('.', ' ').title()
                writer.writerow([
                    name,
                    contact,
                    contact_type.capitalize(),
                    account_name,
                    f"Collected from {account_name} emails"
                ])
    
    return filepath

def is_signature_image(attachment_filename, content_type, payload_size, content_disposition):
    """Check if an attachment is likely a signature image."""
    # Common signature image patterns
    signature_patterns = [
        'signature', 'logo', 'banner', 'footer', 'header',
        'company', 'corporate', 'brand', 'societe', 'entreprise'
    ]
    
    filename_lower = attachment_filename.lower() if attachment_filename else ''
    
    # Check 1: Common signature filenames (only if small)
    if any(pattern in filename_lower for pattern in signature_patterns):
        # Different size limits for different types
        if 'signature' in filename_lower:
            size_limit = 50 * 1024  # Signature images are typically small (< 50KB)
        elif 'logo' in filename_lower:
            size_limit = 60 * 1024  # Logos can be a bit larger (< 60KB)
        else:
            size_limit = 80 * 1024  # Other signature-related images (< 80KB)
        
        if payload_size < size_limit:
            return True
    
    # Check 2: Very small image files (likely logos/signatures)
    if content_type.startswith('image/') and payload_size < 50 * 1024:  # < 50KB
        return True
    
    # Check 3: Inline disposition (embedded images)
    if content_disposition:
        disposition_str = str(content_disposition).lower() if hasattr(content_disposition, 'lower') else str(content_disposition).lower()
        if 'inline' in disposition_str:
            return True
    
    # Check 4: Common image extensions with generic names
    common_image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg']
    if (any(filename_lower.endswith(ext) for ext in common_image_extensions) and
        payload_size < 100 * 1024):  # Small images
        # Check if filename is generic (img1.png, image.jpg, etc.)
        generic_names = ['image', 'img', 'picture', 'pic', 'photo']
        if any(filename_lower.startswith(generic) for generic in generic_names):
            return True
    
    return False


def export_to_markdown(raw_email, export_directory, base_export_directory, num, tags, quote_depth=1, account=None, contacts_collector=None, debug_mode=False):
    """Export an email to Markdown with frontmatter and handle attachments."""
    email_message = email.message_from_bytes(raw_email)

    # Check if email has already been exported (if skip_existing is enabled)
    if account is None:
        account = {}
    skip_existing = account.get('skip_existing', True)
    if skip_existing and email_already_exported(email_message, export_directory):
        return False  # Will be handled by digest in export_folder

    # Analyze email and collect contacts if enabled
    if contacts_collector is not None:
        email_analysis = analyze_email_type(email_message)
        for contact in email_analysis["contacts"]:
            contacts_collector[email_analysis["type"]].add(contact)

    # Add subject hash for uniqueness
    subject = email_message["Subject"]
    if subject:
        # Ensure subject is a string before encoding
        if isinstance(subject, str):
            subject_hash = hashlib.md5(subject.encode()).hexdigest()[:6]
        else:
            # Convert to string if it's not already
            subject_hash = hashlib.md5(str(subject).encode()).hexdigest()[:6]
    else:
        subject_hash = "no-subject"
    
    # Convert email header objects to strings to avoid complex YAML tags
    def header_to_string(header):
        """Convert email header to plain string"""
        if header is None:
            return ""
        if isinstance(header, str):
            return header
        # Handle Header objects and other types
        try:
            return str(header)
        except:
            return ""
    
    frontmatter = {
        "from": header_to_string(email_message["From"]),
        "to": header_to_string(email_message["To"]),
        "date": email.utils.parsedate_to_datetime(email_message["Date"]).isoformat(),
        "subject": header_to_string(email_message["Subject"]),
        "subject_hash": subject_hash,
        "tags": tags,
        "attachments": []
    }

    # Create a descriptive filename
    date_obj = email.utils.parsedate_to_datetime(email_message["Date"])
    date_str = date_obj.strftime("%Y-%m-%d")
    
    # Extract initials or short names for sender and recipient
    def get_short_name(email_str):
        # Handle None values
        if email_str is None:
            return "UNK"
        
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
    
    # Create unique filename: email_YYYY-MM-DD_EFR_to_CAC_<counter>.md
    base_filename = f"email_{date_str}_{sender_short}_to_{recipient_short}"
    
    # Find a unique filename by adding counter if needed
    counter = 1
    filename = f"{base_filename}.md"
    while os.path.exists(os.path.join(export_directory, filename)):
        counter += 1
        filename = f"{base_filename}_{counter}.md"

    body = ""
    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                body = payload.decode(errors="ignore") if isinstance(payload, bytes) else str(payload)
            elif content_type == "text/html" and not body:
                payload = part.get_payload(decode=True)
                body = payload.decode(errors="ignore") if isinstance(payload, bytes) else str(payload)
    else:
        payload = email_message.get_payload(decode=True)
        body = payload.decode(errors="ignore") if isinstance(payload, bytes) else str(payload)

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

    # Use a base name for attachments (without .md extension and counter)
    base_filename_for_attachments = base_filename  # Use the original base without counter
    
    # Get account settings for signature image handling
    skip_signature_images = account.get('skip_signature_images', False) if account else False
    
    for part in email_message.walk():
        if part.get_content_maintype() == 'multipart':
            continue
        if part.get('Content-Disposition') is None:
            continue
        attachment_filename = part.get_filename()
        if attachment_filename:
            # Decode MIME encoded filenames (format: =?utf-8?q?filename?=)
            def decode_mime_filename(encoded_filename, debug=False):
                """Decode MIME encoded filenames"""
                if encoded_filename.startswith('=?') and '?=' in encoded_filename:
                    try:
                        # Parse MIME encoded-word format: =?charset?q?encoded_text?=
                        match = re.match(r'=\?(.*?)\?(.*?)\?(.*?)\?=', encoded_filename)
                        if match:
                            charset = match.group(1)
                            encoding = match.group(2)
                            encoded_text = match.group(3)
                            
                            if encoding.lower() == 'q':
                                # Quoted-printable encoding
                                decoded = quopri.decodestring(encoded_text.replace('_', ' '))
                                return decoded.decode(charset)
                            elif encoding.lower() == 'b':
                                # Base64 encoding
                                decoded = base64.b64decode(encoded_text)
                                return decoded.decode(charset)
                    except Exception as e:
                        if debug:
                            print(f"Debug: Could not decode MIME filename '{encoded_filename}': {e}")
                        return encoded_filename
                return encoded_filename
            
            # Decode the filename if it's MIME encoded
            decoded_filename = decode_mime_filename(attachment_filename, debug_mode)
            
            # Check if this is a signature image that should be skipped
            content_type = part.get_content_type()
            content_disposition = part.get('Content-Disposition', '')
            payload = part.get_payload(decode=True)
            
            if skip_signature_images and is_signature_image(
                decoded_filename, 
                content_type, 
                len(payload) if payload else 0, 
                content_disposition
            ):
                if debug_mode:
                    print(f"    Skipping signature image: '{decoded_filename}' ({len(payload) if payload else 0} bytes)")
                continue
            
            if payload is not None:
                filename_hash = hashlib.md5(decoded_filename.encode()).hexdigest()[:8]
                filepath = os.path.join(attachments_dir, f"{base_filename_for_attachments}_{filename_hash}_{decoded_filename}")
                with open(filepath, 'wb') as f:
                    f.write(payload)
                # Calculate relative path from base export directory to attachments directory
                relative_attachments_path = os.path.relpath(attachments_dir, base_export_directory)
                frontmatter["attachments"].append(f"{relative_attachments_path}/{base_filename_for_attachments}_{filename_hash}_{decoded_filename}")
            else:
                if debug_mode:
                    print(f"    Skipping attachment '{decoded_filename}' with empty payload")

    # Normalize line breaks to max 2 consecutive newlines
    def normalize_line_breaks(text):
        # Replace any sequence of 3 or more newlines with exactly 2 newlines
        return re.sub(r'\n{3,}', '\n\n', text)
    
    # Apply normalization to the email body
    normalized_body = normalize_line_breaks(body)
    
    # Add attachments list to the email body if there are attachments
    if frontmatter["attachments"]:
        attachments_list = "\n\n### Pièces jointes :\n"
        for attachment in frontmatter["attachments"]:
            # Extract just the filename from the full path
            filename_only = os.path.basename(attachment)
            # Create markdown link
            attachments_list += f"- [{filename_only}]({attachment})\n"
        normalized_body += attachments_list
    
    with open(f"{export_directory}/{filename}", "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(frontmatter, f, allow_unicode=True, sort_keys=False)
        f.write("---\n\n")
        f.write(normalized_body)

def export_folder(mail, imap_folder, base_export_directory, account, contacts_collector=None, delete_after_export=False, debug_mode=False):
    """Export all emails from an IMAP folder (including nested folders)."""
    # Handle folder names with spaces and special characters
    # Keep original folder name for IMAP operations, decode for file system
    # Store the original parameter value before any modifications
    original_imap_folder_param = imap_folder  # Store original parameter
    
    # Decode folder name for file system use
    def decode_folder_name_for_filesystem(folder_name):
        """Decode folder name for safe file system use"""
        # Apply the same UTF-7 decoding logic
        utf7_patterns = ['AOk', 'AOg', 'AOk-', 'AOg-', '&AOk', '&AOg']
        if any(pattern in folder_name for pattern in utf7_patterns) or ('&' in folder_name and '-' in folder_name):
            try:
                # Use the same decoding function
                def simple_decode_utf7(s):
                    """Simple UTF-7 decoder for common patterns"""
                    # Replace common encoded sequences
                    s = s.replace('&AOk-', 'é')  # Common French character
                    s = s.replace('&AOg-', 'è')  # Common French character
                    s = s.replace('&AOk', 'é')   # Without dash
                    s = s.replace('&AOg', 'è')   # Without dash
                    s = s.replace('AOk', 'é')    # Without &
                    s = s.replace('AOg', 'è')    # Without &
                    return s
                return simple_decode_utf7(folder_name)
            except:
                pass
        return folder_name
    
    # Use decoded folder name for file system operations
    filesystem_folder = decode_folder_name_for_filesystem(imap_folder)
    
    try:
        # Enhanced UTF-7 decoding function
        def decode_imap_utf7_enhanced(encoded_str):
            """Enhanced IMAP UTF-7 decoder that handles more patterns"""
            import base64
            
            # Standard IMAP UTF-7 decoding
            try:
                # Replace &- with temporary marker
                encoded_str = encoded_str.replace('&-', '&&')
                
                parts = encoded_str.split('&')
                decoded_parts = []
                
                for i, part in enumerate(parts):
                    if i == 0:
                        decoded_parts.append(part)
                    elif part.endswith('-'):
                        # This is an encoded part
                        encoded_part = part[:-1]
                        try:
                            # Add padding if needed
                            padding = '==' if len(encoded_part) % 4 == 2 else '=' if len(encoded_part) % 4 == 3 else ''
                            decoded_bytes = base64.b64decode(encoded_part + padding)
                            decoded_part = decoded_bytes.decode('utf-8')
                            decoded_parts.append(decoded_part)
                        except:
                            decoded_parts.append('&' + part)
                    else:
                        decoded_parts.append('&' + part)
                
                result = ''.join(decoded_parts).replace('&&', '&')
                
                # Apply simple pattern replacements even after base64 decoding
                result = result.replace('AOk-', 'é')
                result = result.replace('AOg-', 'è')
                result = result.replace('AOk', 'é')
                result = result.replace('AOg', 'è')
                result = result.replace('AOk-ry', 'éry')
                result = result.replace('AOg-res', 'ères')
                
                return result
            except:
                pass
            
            # If base64 decoding failed, try simple pattern replacements
            result = encoded_str
            result = result.replace('&AOk-', 'é')
            result = result.replace('&AOg-', 'è')
            result = result.replace('&AOk', 'é')
            result = result.replace('&AOg', 'è')
            result = result.replace('&AOk-ry', 'éry')
            result = result.replace('&AOg-res', 'ères')
            
            # Clean up any remaining & characters
            if '&' in result and not result.startswith('&'):
                result = result.replace('&', '')
            
            return result
        
        # Try multiple selection strategies
        # IMPORTANT: Always use original_imap_folder_param for IMAP server communication
        # The server expects the encoded UTF-7 names, not the decoded ones
        strategies = [original_imap_folder_param]  # Always try the original encoded name first
        if debug_mode:
            print(f"  IMAP strategies: {strategies}")
        
        # Strategy 1: Quoted version of original encoded name (for folders with spaces/special chars)
        special_chars = [' ', '&', '*', '%', '?', '!', '#', '$', '@', '|', '^', '~', '[', ']', '{', '}', '(', ')', ';', ':', '\\', '"', "'"]
        if ' ' in original_imap_folder_param or any(c in original_imap_folder_param for c in special_chars):
            strategies.append(f'"{original_imap_folder_param}"')
        
        # Strategy 2: Try enhanced UTF-7 decoding for display purposes only
        # But still use original for IMAP communication
        if any(pattern in original_imap_folder_param for pattern in ['AOk-', 'AOg-', 'AOk', 'AOg']):
            try:
                decoded_name = decode_imap_utf7_enhanced(original_imap_folder_param)
                if decoded_name != original_imap_folder_param:
                    # For debugging/display only, don't use for IMAP selection
                    if debug_mode:
                        print(f"  Decoded folder name (for display): '{decoded_name}' from '{original_imap_folder_param}'")
            except Exception as e:
                if debug_mode:
                    print(f"  Enhanced UTF-7 decoding failed: {e}")
        

        
        # Strategy 0: First try the EXACT name from the server (most likely to work)
        selected_successfully = False
        try:
            status, messages = mail.select(original_imap_folder_param)
            if status == "OK":
                if debug_mode:
                    print(f"  Selected using exact server name: '{original_imap_folder_param}'")
                selected_successfully = True
            else:
                # If exact name doesn't work, try our strategies
                for strategy in strategies:
                    try:
                        status, messages = mail.select(strategy)
                        if status == "OK":
                            if debug_mode:
                                print(f"  Selected '{original_imap_folder_param}' using strategy: {strategy}")
                            selected_successfully = True
                            break
                    except:
                        continue
        except Exception as e:
            if debug_mode:
                print(f"  Exception selecting folder: {e}")
            # If exact name fails with exception, try our strategies
            for strategy in strategies:
                try:
                    status, messages = mail.select(strategy)
                    if status == "OK":
                        if debug_mode:
                            print(f"  Selected '{original_imap_folder_param}' using strategy: {strategy}")
                        selected_successfully = True
                        break
                except:
                    continue
        
        if not selected_successfully:
            print(f" Unable to select {imap_folder}")
            if debug_mode:
                print(f"  Tried strategies: {strategies}")
            return
    except Exception as e:
        print(f" Error selecting folder '{imap_folder}': {e}")
        return

    status, messages = mail.search(None, "ALL")
    if status != "OK":
        print(f" No emails in {filesystem_folder}")
        return

    # Create export directory, handling folder names with spaces
    # Use the decoded folder name for file system operations
    folder_parts = filesystem_folder.split('/')
    export_directory = os.path.join(base_export_directory, *folder_parts)
    try:
        os.makedirs(export_directory, exist_ok=True)
    except Exception as e:
        print(f"  Could not create directory '{export_directory}': {e}")
        return

    # Initialize digest for skipped emails
    skipped_emails = []
    exported_emails = 0

    for num in messages[0].split():
        status, data = mail.fetch(num, "(RFC822)")
        if status == "OK":
            raw_email = data[0][1]
            quote_depth = account.get('quote_depth', 1)
            result = export_to_markdown(raw_email, export_directory, account['export_directory'], num, [imap_folder], quote_depth, account, contacts_collector, debug_mode)
            if result is False:  # Email was skipped
                email_message = email.message_from_bytes(raw_email)
                subject = email_message['Subject']
                if subject:
                    # Convert to string and limit length
                    subject_str = str(subject)
                    subject = subject_str[:50] if len(subject_str) > 50 else subject_str
                else:
                    subject = "(No subject)"
                skipped_emails.append(subject)
            else:
                exported_emails += 1
            if delete_after_export:
                mail.store(num, '+FLAGS', '\\Deleted')

    if delete_after_export:
        mail.expunge()
    
    # Print digest for skipped emails
    if skipped_emails:
        print(f"{imap_folder}: {exported_emails} exported, {len(skipped_emails)} skipped")
    else:
        print(f"{imap_folder}: {exported_emails} emails exported")

def export_account(account, delete_after_export=False):
    """Export all emails from an account, handling nested folders."""
    print(f"Processing account: {account['name']} → {account['export_directory']}")
    
    # Check if password is available
    if not account.get('password'):
        print(f"Error for {account['name']}: No password found. Check your .env file.")
        return
    
    mail = None
    
    # Initialize contacts collector if enabled
    collect_contacts = account.get('collect_contacts', False)
    contacts_collector = defaultdict(set) if collect_contacts else None
    
    # Enable debug mode if requested
    debug_mode = os.getenv('DEBUG_IMAP', 'false').lower() == 'true'
    
    try:
        if debug_mode:
            print(f"Connecting to {account['server']}:{account['port']}...")
        mail = imaplib.IMAP4_SSL(account["server"], account["port"])
        if debug_mode:
            print(f"Authenticating as {account['username']}...")
        mail.login(account["username"], account["password"])
        if debug_mode:
            print(f"Connected successfully!")

        if debug_mode:
            print("Listing folders...")
        status, folders = mail.list()
        if status != "OK":
            print("Unable to list folders")
            if debug_mode:
                print(f"    IMAP response: {folders}")
            return

        if debug_mode:
            print(f"Found {len(folders)} folder entries from server")
            print("Debug: Raw folder list from IMAP server:")
            for i, folder in enumerate(folders):
                print(f"    {i+1}: {folder}")
        
        processed_folders = set()  # Track processed folders to avoid duplicates
        
        if not folders or len(folders) == 0:
            print("No folders returned by IMAP server")
            if debug_mode:
                print("    Possible causes:")
                print("    - IMAP access not fully enabled")
                print("    - No mailboxes exist")
                print("    - Permission issues")
            return
        
        if debug_mode:
            print("Processing folders...")
        
        # Debug counters
        total_folders = 0
        skipped_invalid = 0
        skipped_duplicates = 0
        skipped_ignored = 0
        processed_count = 0
        
        for folder in folders:
            total_folders += 1
            
            # Extract folder name from IMAP LIST response
            # IMAP LIST format: b'(\Flags) "." folder-name'
            try:
                # Decode and parse the folder line
                folder_str = folder.decode('utf-8', errors='ignore')
                
                # Find the folder name (last part after the flags and delimiter)
                parts = folder_str.split('"')
                if len(parts) >= 3:
                    # Standard format: (flags) "." "folder-name"
                    imap_folder = parts[2].strip()
                else:
                    # Fallback: take last part
                    imap_folder = folder_str.split()[-1].strip('"')
                    
                # Clean up folder name - decode IMAP modified UTF-7 encoding
                # Replace &-encoded characters with their UTF-8 equivalents
                imap_folder = imap_folder.strip()
                
                # Decode IMAP modified UTF-7 encoding
                def decode_imap_utf7(encoded_str, debug=False):
                    """Decode IMAP modified UTF-7 encoding"""
                    try:
                        # IMAP modified UTF-7 uses &- for &, and &XX- for encoded characters
                        # First, replace &- with a temporary marker
                        encoded_str = encoded_str.replace('&-', '&&')
                        
                        # Split into parts separated by &
                        parts = encoded_str.split('&')
                        decoded_parts = []
                        
                        for i, part in enumerate(parts):
                            if i == 0:
                                # First part is not encoded
                                decoded_parts.append(part)
                            elif part.endswith('-'):
                                # This is an encoded part (ends with -)
                                encoded_part = part[:-1]  # Remove the trailing -
                                # Decode from base64-like encoding
                                try:
                                    decoded_bytes = base64.b64decode(encoded_part + '==', validate=True)
                                    decoded_part = decoded_bytes.decode('utf-8')
                                    decoded_parts.append(decoded_part)
                                except:
                                    # If base64 decode fails, keep original
                                    decoded_parts.append('&' + part)
                            else:
                                # This is a literal &
                                decoded_parts.append('&' + part)
                        
                        # Rejoin and fix the temporary marker
                        result = ''.join(decoded_parts).replace('&&', '&')
                        
                        # Additional cleanup: remove any remaining & characters that shouldn't be there
                        if '&' in result and not result.startswith('&'):
                            # Remove standalone & characters (not part of valid encoding)
                            result = result.replace('&', '')
                        
                        # Handle specific French character encodings that might not be caught by base64
                        result = result.replace('AOk', 'é').replace('AOg', 'è')
                        result = result.replace('AOk-', 'é').replace('AOg-', 'è')
                        
                        return result
                    except Exception as e:
                        if debug:
                            print(f"Debug: Could not decode '{encoded_str}': {e}")
                        
                        # Try alternative decoding methods
                        try:
                            # Try direct UTF-8 decode
                            return encoded_str.encode('latin1', errors='ignore').decode('utf-8', errors='ignore')
                        except:
                            pass
                        
                        # Try to create a safe ASCII version
                        try:
                            safe_name = encoded_str.encode('ascii', errors='ignore').decode('ascii')
                            if safe_name and safe_name != encoded_str:
                                if debug_mode:
                                    print(f"Fallback: Using ASCII version '{safe_name}' for '{encoded_str}'")
                                return safe_name
                        except:
                            pass
                        
                        # If all else fails, return original but log it
                        if debug_mode:
                            print(f"Warning: Could not decode folder name '{encoded_str}', using as-is")
                        return encoded_str
                
                # Check if string contains IMAP UTF-7 encoding patterns
                # Look for common French character encodings: é, è, etc.
                utf7_patterns = ['AOk', 'AOg', 'AOk-', 'AOg-', '&AOk', '&AOg']
                original_imap_folder_name = imap_folder  # Save original before decoding
                if any(pattern in imap_folder for pattern in utf7_patterns) or ('&' in imap_folder and '-' in imap_folder):
                    try:
                        decoded_folder = decode_imap_utf7(imap_folder, debug_mode)
                        if debug_mode:
                            print(f"Decoded folder name: '{decoded_folder}' from '{imap_folder}'")
                        imap_folder = decoded_folder
                    except Exception as e:
                        if debug_mode:
                            print(f"Debug: Decoding failed for '{imap_folder}': {e}")
                        # Keep original folder name if decoding fails
                        pass
                
                if debug_mode:
                    print(f"Extracted folder name: '{imap_folder}' from '{folder_str}'")
                    
            except Exception as e:
                print(f"Could not parse folder entry: {folder}")
                if debug_mode:
                    print(f"    Error: {e}")
                continue
            
            # Debug: Show folder being processed
            if debug_mode:
                print(f"Checking folder: {imap_folder}")
            
            # Skip invalid folder names and duplicates
            if not imap_folder or imap_folder == "." or imap_folder.startswith(".."):
                skipped_invalid += 1
                if debug_mode:
                    print(f"Skipping invalid folder: {imap_folder}")
                continue
            
            if imap_folder in processed_folders:
                skipped_duplicates += 1
                if debug_mode:
                    print(f"Skipping duplicate folder: {imap_folder}")
                continue
                
            processed_folders.add(imap_folder)
            
            if imap_folder in account["ignored_folders"]:
                skipped_ignored += 1
                print(f"Ignored folder: {imap_folder}")
                continue
            
            processed_count += 1

            # Handle folder names with spaces and special characters
            try:
                # Keep the original encoded folder name for IMAP selection
                # Use the decoded folder name for file system operations
                # Use the original name saved before UTF-7 decoding
                original_folder_name = original_imap_folder_name if 'original_imap_folder_name' in locals() else imap_folder
                
                # Create display path with decoded folder name for printing
                try:
                    display_path = os.path.join(account['export_directory'], *imap_folder.split('/'))
                except:
                    display_path = f"{account['export_directory']}/{imap_folder}"
                
                print(f"Exporting {imap_folder} → {display_path}")
                export_folder(mail, original_folder_name, account["export_directory"], account, contacts_collector, delete_after_export, debug_mode)
            except Exception as e:
                error_msg = str(e)
                print(f"  Could not process folder '{imap_folder}': {error_msg}")
                if debug_mode:
                    print(f"    Full error: {traceback.format_exc()}")
                
                # Try to continue with a simplified folder name
                if "replace" in error_msg.lower() or "encoding" in error_msg.lower():
                    try:
                        # Try to create a safe version of the folder name
                        safe_name = imap_folder.encode('ascii', errors='ignore').decode('ascii')
                        if safe_name:
                            print(f"    Retrying with simplified name: '{safe_name}'")
                            # Here you would add logic to retry with safe_name
                    except:
                        pass
                continue

        # Only close if we're in SELECTED state, otherwise just logout
        try:
            mail.close()
        except:
            pass  # Ignore close errors (e.g., not in SELECTED state)
        
        # Show folder processing summary
        print(f"Folder processing summary for {account['name']}:")
        print(f"    Total folders found: {total_folders}")
        print(f"    Invalid/empty names: {skipped_invalid}")
        print(f"    Duplicate folders: {skipped_duplicates}")
        print(f"    Ignored by config: {skipped_ignored}")
        print(f"    Processed folders: {processed_count}")
        
        # Check if any folders were processed
        if processed_count == 0:
            print(f"No folders processed for {account['name']}")
            if skipped_ignored > 0:
                print(f"    All folders were ignored (check your ignored_folders config)")
            elif skipped_invalid > 0:
                print(f"    All folders had invalid names")
            else:
                print(f"    This might indicate a permission issue or empty mailbox")
        else:
            print(f"Successfully processed {processed_count} folders")
        
        # Generate contacts file if contacts were collected
        if collect_contacts and contacts_collector:
            if contacts_collector:
                contacts_file = generate_contacts_file(contacts_collector, account['export_directory'], account['name'])
                print(f"Generated contacts file: {os.path.basename(contacts_file)}")
            else:
                print(f"No contacts found for {account['name']}")
        
        mail.logout()
        print(f"Export completed for {account['name']}\n")

    except imaplib.IMAP4.error as e:
        error_msg = str(e)
        if "LOGIN failed" in error_msg or "authentication failed" in error_msg.lower():
            print(f"Authentication failed for {account['name']}: Wrong username or password")
            print(f"    Check your .env file and account configuration")
        elif "connection refused" in error_msg.lower() or "timeout" in error_msg.lower():
            print(f"Connection failed for {account['name']}: Could not connect to server")
            print(f"    Check server address: {account['server']}:{account['port']}")
            print(f"    Verify the server is accessible and IMAP is enabled")
        else:
            print(f"IMAP error for {account['name']}: {error_msg}")
        try:
            if mail:
                mail.logout()
        except:
            pass
    except Exception as e:
        print(f"Unexpected error for {account['name']}: {e}")
        try:
            if mail:
                mail.logout()
        except:
            pass

def main():
    """Main function to run the email export."""
    parser = argparse.ArgumentParser(description='Export emails from IMAP accounts to Markdown')
    parser.add_argument('--account', help='Export only specific account(s) - comma separated', 
                       default=None)
    parser.add_argument('--list-accounts', help='List available accounts', action='store_true')
    parser.add_argument('--all', help='Export all accounts (default)', action='store_true')
    parser.add_argument('--delete-after-export', help='Delete emails after export (dangerous!)', 
                       action='store_true')
    
    args = parser.parse_args()
    
    # Handle --list-accounts option
    if args.list_accounts:
        print("📋 Available accounts from accounts.yaml:")
        for i, account in enumerate(config['accounts'], 1):
            export_dir = account.get('export_directory', 'Not configured')
            print(f"   {i}. {account['name']} → {export_dir}")
        return
    
    # Determine which accounts to export
    accounts_to_export = []
    
    if args.account:
        # Export only specified accounts (comma-separated, case-insensitive)
        account_names = [name.strip() for name in args.account.split(',')]
        for account in config['accounts']:
            if account['name'].lower() in [name.lower() for name in account_names]:
                accounts_to_export.append(account)
                print(f"🎯 Selected account for export: {account['name']}")
            else:
                print(f"📥 Skipping account: {account['name']}")
    elif args.all or not args.account:
        # Export all accounts (default behavior)
        accounts_to_export = config['accounts']
        print(f"📧 Exporting all {len(accounts_to_export)} accounts")
    
    # Check if any accounts were selected
    if not accounts_to_export:
        print("❌ No accounts selected for export")
        print("Available accounts:")
        for account in config['accounts']:
            print(f"   - {account['name']}")
        print("\nUsage:")
        print(f"   python3 {sys.argv[0]} --account Gmail")
        print(f"   python3 {sys.argv[0]} --account Gmail,LaContreVoie")
        print(f"   python3 {sys.argv[0]} --all")
        print(f"   python3 {sys.argv[0]} --list-accounts")
        return
    
    # Run export for selected accounts
    for account in accounts_to_export:
        export_account(account, delete_after_export=args.delete_after_export)

if __name__ == "__main__":
    main()
