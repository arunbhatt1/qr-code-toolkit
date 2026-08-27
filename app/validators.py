"""Input validation routines for QR Code Toolkit.

Provides validation and normalization for all supported QR payload types with
clear, user-friendly error messages and zero stack-trace leakage.
"""

from __future__ import annotations

import re
from typing import Tuple
from urllib.parse import urlparse

# Regular expressions for validation
_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)
# Allows international numbers with +, spaces, dashes, dots, parentheses, and digits
_PHONE_REGEX = re.compile(r"^\+?[0-9\s\-\.\(\)]{3,25}$")


def validate_text(text: str) -> Tuple[bool, str]:
    """Validate plain text content."""
    if not text or not text.strip():
        return False, "Text content cannot be empty."
    return True, ""


def normalize_and_validate_url(raw_url: str) -> Tuple[bool, str, str]:
    """Validate and optionally normalize URL.

    Returns:
        (is_valid, normalized_url, error_message)
    """
    cleaned = raw_url.strip()
    if not cleaned:
        return False, "", "URL cannot be empty."

    # If scheme is missing, prepend https://
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", cleaned):
        cleaned = f"https://{cleaned}"

    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in ("http", "https"):
        return False, "", "URL scheme must be http:// or https://"

    host = (parsed.hostname or "").lower()
    if not host or ("." not in host and host not in ("localhost", "127.0.0.1")):
        # Check if it's IP address
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
            return False, "", "Please enter a valid domain name (e.g., example.com)."

    # Reject spaces or illegal control characters in domain
    if any(char in parsed.netloc for char in " \t\r\n<>\"'"):
        return False, "", "URL contains invalid characters in the host address."

    return True, cleaned, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email address format."""
    cleaned = email.strip()
    if not cleaned:
        return False, "Email address cannot be empty."
    if not _EMAIL_REGEX.match(cleaned):
        return False, "Please enter a valid email address (e.g., user@example.com)."
    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    """Validate phone number format."""
    cleaned = phone.strip()
    if not cleaned:
        return False, "Phone number cannot be empty."
    if not _PHONE_REGEX.match(cleaned):
        return False, "Please enter a valid phone number (e.g., +1 234 567 8900)."
    # Ensure at least 3 digits exist
    digits_only = re.sub(r"\D", "", cleaned)
    if len(digits_only) < 3:
        return False, "Phone number must contain at least 3 digits."
    return True, ""


def validate_wifi(
    ssid: str, password: str, security: str
) -> Tuple[bool, str]:
    """Validate Wi-Fi network parameters."""
    cleaned_ssid = ssid.strip()
    if not cleaned_ssid:
        return False, "Wi-Fi Network Name (SSID) is required."

    sec = security.upper()
    if sec not in ("WPA", "WPA2", "WPA3", "WEP", "NONE", "NOPASS"):
        return False, f"Unsupported security type '{security}'."

    if sec in ("WPA", "WPA2", "WPA3", "WEP"):
        if not password:
            return False, f"Password is required for {sec} secured networks."
        if sec in ("WPA", "WPA2", "WPA3") and len(password) < 8:
            return (
                False,
                f"{sec} passwords should be at least 8 characters long.",
            )

    return True, ""


def validate_vcard(
    full_name: str,
    org: str = "",
    phone: str = "",
    email: str = "",
    website: str = "",
    address: str = "",
) -> Tuple[bool, str]:
    """Validate contact information for vCard generation."""
    has_any_field = any(
        f.strip() for f in (full_name, org, phone, email, website, address)
    )
    if not has_any_field:
        return (
            False,
            "At least one contact field (e.g., Name, Phone, Email) must be provided.",
        )

    if email.strip():
        ok, msg = validate_email(email)
        if not ok:
            return False, msg

    if phone.strip():
        ok, msg = validate_phone(phone)
        if not ok:
            return False, msg

    if website.strip():
        ok, _, msg = normalize_and_validate_url(website)
        if not ok:
            return False, f"Contact website error: {msg}"

    return True, ""


def validate_sms(phone: str, message: str = "") -> Tuple[bool, str]:
    """Validate SMS parameters."""
    return validate_phone(phone)


def validate_location(latitude_str: str, longitude_str: str) -> Tuple[bool, float, float, str]:
    """Validate geographic coordinates.

    Returns:
        (is_valid, lat_float, lon_float, error_message)
    """
    if not latitude_str.strip() or not longitude_str.strip():
        return False, 0.0, 0.0, "Both Latitude and Longitude are required."

    try:
        lat = float(latitude_str.strip())
    except ValueError:
        return False, 0.0, 0.0, "Latitude must be a valid number between -90 and 90."

    try:
        lon = float(longitude_str.strip())
    except ValueError:
        return False, 0.0, 0.0, "Longitude must be a valid number between -180 and 180."

    if not (-90.0 <= lat <= 90.0):
        return False, 0.0, 0.0, "Latitude must be between -90.0 and +90.0 degrees."

    if not (-180.0 <= lon <= 180.0):
        return False, 0.0, 0.0, "Longitude must be between -180.0 and +180.0 degrees."

    return True, lat, lon, ""
