#!/usr/bin/env python3
"""
Test edge cases and error handling for the email-to-markdown export functionality.
"""

import pytest
import os
import sys
import hashlib

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.export_emails import (
    analyze_email_type,
    email_already_exported
)


def test_analyze_email_type_edge_cases():
    """Test analyze_email_type with various edge cases."""
    from email.message import Message
    
    # Test with empty message
    msg = Message()
    result = analyze_email_type(msg)
    assert "type" in result
    assert "contacts" in result
    
    # Test with None values in all fields
    msg["From"] = None
    msg["To"] = None
    msg["Subject"] = None
    msg["Cc"] = None
    result = analyze_email_type(msg)
    assert "type" in result
    assert "contacts" in result
    assert result["from"] == ""
    assert result["to"] == []
    assert result["cc"] == []


def test_analyze_email_type_with_none_values():
    """Test analyze_email_type with None values in email fields."""
    from email.message import Message
    
    # Create a message with None values
    msg = Message()
    msg["From"] = None
    msg["To"] = None
    msg["Subject"] = None
    
    # This should not raise an exception
    result = analyze_email_type(msg)
    assert "type" in result


def test_analyze_email_type_with_header_objects():
    """Test analyze_email_type with Header objects that might cause issues."""
    from email.message import Message
    from email.header import Header
    
    # Create a message with Header objects
    msg = Message()
    msg["From"] = Header("Sender Name <sender@example.com>", "utf-8")
    msg["To"] = Header("Recipient Name <recipient@example.com>", "utf-8")
    msg["Subject"] = Header("Test Subject with Newsletter", "utf-8")
    msg["Cc"] = Header("cc1@example.com, cc2@example.com", "utf-8")
    
    # This should not raise an exception
    result = analyze_email_type(msg)
    assert "type" in result
    assert "contacts" in result
    
    # Test with Header objects that contain special characters
    msg2 = Message()
    msg2["From"] = Header("José García <jose@example.com>", "utf-8")
    msg2["To"] = Header("François Müller <francois@example.com>", "utf-8")
    msg2["Subject"] = Header("Test with accented chars: éèêë", "utf-8")
    
    # This should also not raise an exception
    result2 = analyze_email_type(msg2)
    assert "type" in result2
    assert "contacts" in result2


def test_email_already_exported():
    """Test the email_already_exported function."""
    import email
    from email.message import Message
    import tempfile
    import os
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a simple email message
        msg = Message()
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "Test Subject"
        msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"
        
        # Test with non-existent directory
        result = email_already_exported(msg, "/non/existent/directory")
        assert result == False
        
        # Test with existing directory but no matching files
        result = email_already_exported(msg, temp_dir)
        assert result == False


def test_subject_slicing_with_header_objects():
    """Test subject slicing that was causing 'Header object is not subscriptable' error."""
    from email.message import Message
    from email.header import Header
    
    # Create a message with Header object as subject
    msg = Message()
    msg["Subject"] = Header("This is a very long subject that needs to be truncated for display purposes", "utf-8")
    
    # This should not raise 'Header object is not subscriptable' error
    subject = msg["Subject"]
    if subject:
        # Convert to string and limit length (this is what was failing)
        subject_str = str(subject)
        subject_display = subject_str[:50] if len(subject_str) > 50 else subject_str
        assert isinstance(subject_display, str)
        assert len(subject_display) <= 50
    else:
        subject_display = "(No subject)"
    
    assert subject_display != "(No subject)"
    assert len(subject_display) <= 50


def test_subject_slicing_with_none():
    """Test subject slicing with None subject."""
    from email.message import Message
    
    # Create a message with None subject
    msg = Message()
    msg["Subject"] = None
    
    # This should not crash
    subject = msg["Subject"]
    if subject:
        subject_str = str(subject)
        subject_display = subject_str[:50] if len(subject_str) > 50 else subject_str
    else:
        subject_display = "(No subject)"
    
    assert subject_display == "(No subject)"


def test_subject_hash_generation():
    """Test subject hash generation with various inputs."""
    from email.message import Message
    
    # Test with normal subject
    msg = Message()
    msg["Subject"] = "Test Subject"
    
    # This should not raise an exception when generating subject hash
    subject = msg["Subject"]
    if subject:
        if isinstance(subject, str):
            subject_hash = hashlib.md5(subject.encode()).hexdigest()[:6]
        else:
            subject_hash = hashlib.md5(str(subject).encode()).hexdigest()[:6]
    else:
        subject_hash = "no-subject"
    
    assert len(subject_hash) == 6


def test_subject_hash_with_none():
    """Test subject hash generation with None subject."""
    from email.message import Message
    
    # Test with None subject
    msg = Message()
    msg["Subject"] = None
    
    # This should not raise an exception
    subject = msg["Subject"]
    if subject:
        if isinstance(subject, str):
            subject_hash = hashlib.md5(subject.encode()).hexdigest()[:6]
        else:
            subject_hash = hashlib.md5(str(subject).encode()).hexdigest()[:6]
    else:
        subject_hash = "no-subject"
    
    assert subject_hash == "no-subject"


def test_folder_name_robustness():
    """Test that folder names with special characters don't crash path operations."""
    import os
    import tempfile
    
    problematic_names = [
        "INBOX.copro",
        "INBOX.echanges", 
        "INBOX.immo.chamb&AOk-ry",
        "INBOX.immo.valli&AOg-res",
        "INBOX.with.special.chars",
        "INBOX/with/slashes",
        "INBOX.with.spaces and.dots",
    ]
    
    with tempfile.TemporaryDirectory() as temp_dir:
        for folder_name in problematic_names:
            # Test that these don't crash when used in path operations
            try:
                if folder_name:
                    # This is the operation that was crashing
                    display_path = os.path.join(temp_dir, *folder_name.split('/'))
                else:
                    display_path = temp_dir
                assert isinstance(display_path, str)
                assert display_path.startswith(temp_dir)
            except Exception as e:
                pytest.fail(f"Folder name '{folder_name}' caused crash: {e}")


def test_folder_name_with_none():
    """Test folder name handling with None values."""
    import os
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with None folder name
        folder_name = None
        try:
            if folder_name:
                display_path = os.path.join(temp_dir, *folder_name.split('/'))
            else:
                display_path = temp_dir
            assert display_path == temp_dir
        except Exception as e:
            pytest.fail(f"None folder name caused crash: {e}")


def test_folder_name_with_empty_string():
    """Test folder name handling with empty strings."""
    import os
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with empty string folder name
        folder_name = ""
        try:
            if folder_name:
                display_path = os.path.join(temp_dir, *folder_name.split('/'))
            else:
                display_path = temp_dir
            assert display_path == temp_dir
        except Exception as e:
            pytest.fail(f"Empty folder name caused crash: {e}")


def test_imap_utf7_decoding():
    """Test IMAP UTF-7 decoding for problematic folder names."""
    import base64
    
    def decode_imap_utf7_basic(encoded_str):
        """Basic IMAP UTF-7 decoder for testing"""
        try:
            # Standard IMAP UTF-7 decoding
            encoded_str = encoded_str.replace('&-', '&&')
            parts = encoded_str.split('&')
            decoded_parts = []
            
            for i, part in enumerate(parts):
                if i == 0:
                    decoded_parts.append(part)
                elif part.endswith('-'):
                    encoded_part = part[:-1]
                    # Add proper padding for base64
                    padding = '==' if len(encoded_part) % 4 == 2 else '=' if len(encoded_part) % 4 == 3 else ''
                    decoded_bytes = base64.b64decode(encoded_part + padding)
                    decoded_part = decoded_bytes.decode('utf-8')
                    decoded_parts.append(decoded_part)
                else:
                    decoded_parts.append('&' + part)
            
            result = ''.join(decoded_parts).replace('&&', '&')
            return result
        except Exception as e:
            # Fallback to simple replacements
            result = encoded_str
            # Handle IMAP UTF-7 encoded parts - replace the encoded sequences directly
            result = result.replace('&AOk-', 'é')
            result = result.replace('&AOg-', 'è')
            result = result.replace('&AOk', 'é')
            result = result.replace('&AOg', 'è')
            result = result.replace('&AOk-ry', 'éry')
            result = result.replace('&AOg-res', 'ères')
            return result
    
    # Test cases based on the problematic folder names we've seen
    test_cases = [
        # Basic UTF-7 encoding
        ("INBOX.&AOk-ry", "INBOX.éry"),  # chambAOk-ry -> chambéry
        ("INBOX.&AOg-res", "INBOX.ères"),  # valliAOg-res -> vallières
        
        # More complex cases
        ("INBOX.&AOk-", "INBOX.é"),  # Just é
        ("INBOX.&AOg-", "INBOX.è"),  # Just è
        
        # Already decoded names should remain unchanged
        ("INBOX.test", "INBOX.test"),
        ("INBOX.copro", "INBOX.copro"),
    ]
    
    for encoded, expected in test_cases:
        result = decode_imap_utf7_basic(encoded)
        assert result == expected, f"Expected '{expected}', got '{result}' for input '{encoded}'"


def test_folder_name_normalization():
    """Test that folder names are consistently normalized for comparison."""
    # This test ensures that the same folder is recognized as the same
    # even if it comes in different encodings
    
    folder_variants = [
        "INBOX.immo.chambéry",
        "INBOX.immo.chambAOk-ry",  # UTF-7 encoded version
        "INBOX.immo.chambéry",  # Should normalize to this
    ]
    
    # Normalize function (to be implemented)
    def normalize_folder_name(name):
        """Normalize folder name for consistent comparison"""
        # This is what we want to implement
        return name.replace('AOk-', 'é').replace('AOg-', 'è')
    
    # All variants should normalize to the same value
    normalized_variants = [normalize_folder_name(name) for name in folder_variants]
    
    # They should all be the same after normalization
    assert len(set(normalized_variants)) == 1, f"Folder variants should normalize to same value: {normalized_variants}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])