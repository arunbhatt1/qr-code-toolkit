"""Standardized QR payload generators.

Generates compliant payload strings for Text, URL, Wi-Fi, vCard 3.0, Email,
Phone, SMS, and Geo Location with proper RFC and protocol escaping.
Never logs or persists sensitive payload parameters.
"""

from __future__ import annotations

import urllib.parse
from typing import Optional

from app.validators import (
    normalize_and_validate_url,
    validate_email,
    validate_location,
    validate_phone,
    validate_sms,
    validate_text,
    validate_vcard,
    validate_wifi,
)


def _escape_wifi_string(value: str) -> str:
    """Escape special characters according to ZXing Wi-Fi QR specification.

    Characters to escape: \\ ; , : "
    """
    if not value:
        return ""
    escaped = []
    for ch in value:
        if ch in ("\\", ";", ",", ":", '"'):
            escaped.append(f"\\{ch}")
        else:
            escaped.append(ch)
    return "".join(escaped)


def _escape_vcard_string(value: str) -> str:
    """Escape special characters for vCard 3.0 fields."""
    if not value:
        return ""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def build_text_payload(text: str) -> str:
    """Build plain text payload."""
    ok, msg = validate_text(text)
    if not ok:
        raise ValueError(msg)
    return text.strip()


def build_url_payload(raw_url: str) -> str:
    """Build normalized URL payload."""
    ok, normalized, msg = normalize_and_validate_url(raw_url)
    if not ok:
        raise ValueError(msg)
    return normalized


def build_wifi_payload(
    ssid: str,
    password: str = "",
    security: str = "WPA",
    hidden: bool = False,
) -> str:
    """Build standard Wi-Fi network QR payload.

    Format: WIFI:T:<WPA|WEP|nopass>;S:<SSID>;P:<password>;H:<true|false>;;
    """
    ok, msg = validate_wifi(ssid, password, security)
    if not ok:
        raise ValueError(msg)

    sec_type = security.upper()
    if sec_type in ("WPA", "WPA2", "WPA3"):
        sec_str = "WPA"
    elif sec_type == "WEP":
        sec_str = "WEP"
    else:
        sec_str = "nopass"

    escaped_ssid = _escape_wifi_string(ssid.strip())
    escaped_password = _escape_wifi_string(password)
    hidden_str = "true" if hidden else "false"

    if sec_str == "nopass":
        return f"WIFI:T:nopass;S:{escaped_ssid};H:{hidden_str};;"
    return f"WIFI:T:{sec_str};S:{escaped_ssid};P:{escaped_password};H:{hidden_str};;"


def build_vcard_payload(
    full_name: str,
    org: str = "",
    phone: str = "",
    email: str = "",
    website: str = "",
    address: str = "",
) -> str:
    """Build standard vCard 3.0 contact payload."""
    ok, msg = validate_vcard(full_name, org, phone, email, website, address)
    if not ok:
        raise ValueError(msg)

    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
    ]

    cleaned_name = full_name.strip()
    if cleaned_name:
        parts = cleaned_name.split(None, 1)
        if len(parts) > 1:
            first_name, last_name = parts[0], parts[1]
        else:
            first_name, last_name = parts[0], ""
        lines.append(
            f"N:{_escape_vcard_string(last_name)};{_escape_vcard_string(first_name)};;;"
        )
        lines.append(f"FN:{_escape_vcard_string(cleaned_name)}")

    if org.strip():
        lines.append(f"ORG:{_escape_vcard_string(org.strip())}")

    if phone.strip():
        lines.append(f"TEL;TYPE=CELL,VOICE:{phone.strip()}")

    if email.strip():
        lines.append(f"EMAIL;TYPE=INTERNET:{email.strip()}")

    if website.strip():
        ok_url, norm_url, _ = normalize_and_validate_url(website)
        if ok_url:
            lines.append(f"URL:{norm_url}")

    if address.strip():
        lines.append(f"ADR;TYPE=WORK:;;{_escape_vcard_string(address.strip())};;;;")

    lines.append("END:VCARD")
    return "\r\n".join(lines)


def build_email_payload(
    email: str,
    subject: str = "",
    body: str = "",
) -> str:
    """Build mailto: URI payload."""
    ok, msg = validate_email(email)
    if not ok:
        raise ValueError(msg)

    params = {}
    if subject.strip():
        params["subject"] = subject.strip()
    if body.strip():
        params["body"] = body.strip()

    query_str = urllib.parse.urlencode(params) if params else ""
    if query_str:
        return f"mailto:{email.strip()}?{query_str}"
    return f"mailto:{email.strip()}"


def build_phone_payload(phone: str) -> str:
    """Build tel: URI payload."""
    ok, msg = validate_phone(phone)
    if not ok:
        raise ValueError(msg)
    # Remove unnecessary spaces or format cleanly
    clean_num = "".join(ch for ch in phone.strip() if ch in "+0123456789")
    if not clean_num:
        clean_num = phone.strip()
    return f"tel:{clean_num}"


def build_sms_payload(phone: str, message: str = "") -> str:
    """Build standard SMSTO: payload."""
    ok, msg = validate_sms(phone, message)
    if not ok:
        raise ValueError(msg)

    clean_num = "".join(ch for ch in phone.strip() if ch in "+0123456789")
    if not clean_num:
        clean_num = phone.strip()

    if message.strip():
        return f"SMSTO:{clean_num}:{message.strip()}"
    return f"SMSTO:{clean_num}:"


def build_location_payload(
    latitude: float | str,
    longitude: float | str,
) -> str:
    """Build geo: URI payload (geo:latitude,longitude)."""
    ok, lat, lon, msg = validate_location(str(latitude), str(longitude))
    if not ok:
        raise ValueError(msg)
    return f"geo:{lat:.6f},{lon:.6f}"
