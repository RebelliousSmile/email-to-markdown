#!/usr/bin/env python3
"""
Basic tests for the email-to-markdown export functionality.
"""

import pytest
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from export_emails import (
    limit_quote_depth,
    analyze_email_type,
    email_already_exported
)


def test_limit_quote_depth():
    """Test the limit_quote_depth function."""
    # Test basic quote limiting
    text = "Hello\n> First quote\n>> Second quote\n>>> Third quote\n> Back to first"
    result = limit_quote_depth(text, max_depth=1)
    expected = "Hello\n> First quote\n> Back to first"
    assert result == expected
    
    # Test with no quotes
    text = "Hello\nWorld"
    result = limit_quote_depth(text, max_depth=1)
    assert result == text


def test_email_already_exported():
    """Test the email_already_exported function."""
    from email.message import Message
    import tempfile
    
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





def test_analyze_email_type():
    """Test the analyze_email_type function."""
    import email
    from email.message import Message
    
    # Create a simple email message
    msg = Message()
    msg["From"] = "sender@example.com"
    msg["To"] = "recipient@example.com"
    msg["Subject"] = "Test email"
    
    result = analyze_email_type(msg)
    assert result["type"] == "direct"
    assert result["from"] == "sender@example.com"
    assert "recipient@example.com" in result["to"]


def test_analyze_email_type_with_header_objects():
    """Test analyze_email_type with Header objects."""
    import email
    from email.message import Message
    from email.header import Header
    
    # Create a message with Header objects
    msg = Message()
    msg["From"] = Header("Sender Name", "utf-8")
    msg["To"] = "recipient@example.com"
    msg["Subject"] = Header("Test Subject", "utf-8")
    
    # This should not raise an exception
    result = analyze_email_type(msg)
    assert "type" in result


def test_signature_image_detection():
    """Test the signature image detection function."""
    from export_emails import is_signature_image
    
    # Test signature images (should be detected)
    assert is_signature_image("signature.png", "image/png", 1024, "inline") == True
    assert is_signature_image("logo.jpg", "image/jpeg", 5120, "attachment") == True
    assert is_signature_image("company_banner.gif", "image/gif", 2048, "inline") == True
    assert is_signature_image("image1.png", "image/png", 8192, "inline") == True  # Generic name + small
    
    # Test real attachments (should NOT be detected as signature)
    assert is_signature_image("contract.pdf", "application/pdf", 102400, "attachment") == False
    assert is_signature_image("photo_vacation.jpg", "image/jpeg", 2048000, "attachment") == False  # Large image
    assert is_signature_image("document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 51200, "attachment") == False
    
    # Edge cases
    assert is_signature_image("large_signature.png", "image/png", 60000, "attachment") == False  # Too large for signature
    assert is_signature_image("small_document.txt", "text/plain", 1024, "attachment") == False  # Small but not image


if __name__ == "__main__":
    pytest.main([__file__, "-v"])