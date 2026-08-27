"""QR Code scanner, screen capture decoder, camera engine, and payload parser."""

from __future__ import annotations

import re
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image, ImageGrab

from app.logging_config import log_error, log_scan_event


@dataclass
class DecodedQRResult:
    """Structured representation of a scanned QR code."""

    raw_text: str
    qr_type: str  # "url", "wifi", "vcard", "email", "phone", "sms", "location", "text"
    parsed_data: Dict[str, Any] = field(default_factory=dict)
    points: Optional[np.ndarray] = None
    bounding_box: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)


def parse_payload(raw_text: str) -> DecodedQRResult:
    """Parse raw decoded string into a structured, type-specific QR result."""
    text = raw_text.strip()
    if not text:
        return DecodedQRResult(raw_text="", qr_type="text", parsed_data={"text": ""})

    # 1. Wi-Fi: WIFI:T:WPA;S:MySSID;P:MyPassword;H:false;;
    if text.upper().startswith("WIFI:"):
        data: Dict[str, Any] = {
            "ssid": "",
            "password": "",
            "security": "WPA",
            "hidden": False,
        }
        # Extract fields using regex for escaped strings
        ssid_m = re.search(r"(?<!\\)S:((?:\\;|[^;])*)", text)
        pass_m = re.search(r"(?<!\\)P:((?:\\;|[^;])*)", text)
        type_m = re.search(r"(?<!\\)T:((?:\\;|[^;])*)", text)
        hid_m = re.search(r"(?<!\\)H:((?:\\;|[^;])*)", text)

        if ssid_m:
            data["ssid"] = ssid_m.group(1).replace(r"\;", ";").replace(r"\:", ":").replace(r"\\", "\\")
        if pass_m:
            data["password"] = pass_m.group(1).replace(r"\;", ";").replace(r"\:", ":").replace(r"\\", "\\")
        if type_m:
            data["security"] = type_m.group(1).upper()
        if hid_m:
            data["hidden"] = hid_m.group(1).lower() in ("true", "1")

        return DecodedQRResult(raw_text=raw_text, qr_type="wifi", parsed_data=data)

    # 2. vCard: BEGIN:VCARD ... END:VCARD
    if "BEGIN:VCARD" in text.upper():
        vcard_data: Dict[str, str] = {
            "name": "",
            "org": "",
            "phone": "",
            "email": "",
            "website": "",
            "address": "",
        }
        for line in text.splitlines():
            line_str = line.strip()
            if not line_str or ":" not in line_str:
                continue
            key_part, val_part = line_str.split(":", 1)
            key_clean = key_part.split(";")[0].upper()
            val_clean = (
                val_part.replace(r"\n", "\n")
                .replace(r"\,", ",")
                .replace(r"\;", ";")
                .replace(r"\\", "\\")
            )

            if key_clean == "FN" and not vcard_data["name"]:
                vcard_data["name"] = val_clean
            elif key_clean == "N" and not vcard_data["name"]:
                # N:Last;First;;;
                parts = [p for p in val_clean.split(";") if p]
                vcard_data["name"] = " ".join(reversed(parts)) if parts else val_clean
            elif key_clean == "ORG":
                vcard_data["org"] = val_clean
            elif key_clean in ("TEL", "PHONE"):
                vcard_data["phone"] = val_clean
            elif key_clean == "EMAIL":
                vcard_data["email"] = val_clean
            elif key_clean in ("URL", "WEBSITE"):
                vcard_data["website"] = val_clean
            elif key_clean == "ADR":
                adr_parts = [p for p in val_clean.split(";") if p]
                vcard_data["address"] = ", ".join(adr_parts)

        return DecodedQRResult(raw_text=raw_text, qr_type="vcard", parsed_data=vcard_data)

    # 3. Email: mailto:user@example.com?subject=...&body=...
    if text.lower().startswith("mailto:"):
        raw_target = text[7:]
        email_addr = raw_target.split("?")[0]
        parsed_email: Dict[str, str] = {"email": email_addr, "subject": "", "body": ""}

        if "?" in raw_target:
            query = raw_target.split("?", 1)[1]
            params = urllib.parse.parse_qs(query)
            parsed_email["subject"] = params.get("subject", [""])[0]
            parsed_email["body"] = params.get("body", [""])[0]

        return DecodedQRResult(raw_text=raw_text, qr_type="email", parsed_data=parsed_email)

    # 4. Phone: tel:+1234567890
    if text.lower().startswith("tel:"):
        phone_number = text[4:]
        return DecodedQRResult(
            raw_text=raw_text,
            qr_type="phone",
            parsed_data={"phone": phone_number},
        )

    # 5. SMS: SMSTO:+1234567890:Hello or sms:+1234567890?body=Hello
    if text.upper().startswith("SMSTO:"):
        parts = text[6:].split(":", 1)
        phone = parts[0]
        body = parts[1] if len(parts) > 1 else ""
        return DecodedQRResult(
            raw_text=raw_text,
            qr_type="sms",
            parsed_data={"phone": phone, "message": body},
        )
    if text.lower().startswith("sms:"):
        raw_sms = text[4:]
        phone = raw_sms.split("?")[0]
        body = ""
        if "?" in raw_sms:
            params = urllib.parse.parse_qs(raw_sms.split("?", 1)[1])
            body = params.get("body", [""])[0]
        return DecodedQRResult(
            raw_text=raw_text,
            qr_type="sms",
            parsed_data={"phone": phone, "message": body},
        )

    # 6. Geo Location: geo:latitude,longitude
    if text.lower().startswith("geo:"):
        geo_str = text[4:].split("?")[0]
        lat_lon = geo_str.split(",")
        if len(lat_lon) >= 2:
            try:
                lat = float(lat_lon[0].strip())
                lon = float(lat_lon[1].strip())
                maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                return DecodedQRResult(
                    raw_text=raw_text,
                    qr_type="location",
                    parsed_data={"latitude": lat, "longitude": lon, "maps_url": maps_url},
                )
            except ValueError:
                pass

    # 7. URL: http:// or https:// or www.
    if text.lower().startswith(("http://", "https://", "ftp://", "www.")):
        full_url = f"https://{text}" if text.lower().startswith("www.") else text
        parsed_u = urllib.parse.urlparse(full_url)
        return DecodedQRResult(
            raw_text=raw_text,
            qr_type="url",
            parsed_data={"url": full_url, "domain": parsed_u.netloc},
        )

    # 8. Plain Text fallback
    return DecodedQRResult(
        raw_text=raw_text,
        qr_type="text",
        parsed_data={"text": text},
    )


class QRScanner:
    """Local, offline QR code detector and scanner using OpenCV."""

    def __init__(self) -> None:
        self.detector = cv2.QRCodeDetector()

    def _to_cv2_image(
        self,
        image_input: Union[str, Path, Image.Image, np.ndarray],
    ) -> Optional[np.ndarray]:
        """Convert various input types into a standard BGR OpenCV numpy array."""
        if isinstance(image_input, (str, Path)):
            path_str = str(image_input)
            if not Path(path_str).exists():
                return None
            # Use imdecode to support Unicode file paths on Windows
            data = np.fromfile(path_str, dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            return img
        elif isinstance(image_input, Image.Image):
            rgb = image_input.convert("RGB")
            return cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, np.ndarray):
            if len(image_input.shape) == 2:
                return cv2.cvtColor(image_input, cv2.COLOR_GRAY2BGR)
            elif image_input.shape[2] == 4:
                return cv2.cvtColor(image_input, cv2.COLOR_RGBA2BGR)
            return image_input
        return None

    def scan_image(
        self,
        image_input: Union[str, Path, Image.Image, np.ndarray],
    ) -> List[DecodedQRResult]:
        """Detect and decode QR code(s) from an image with adaptive pre-processing."""
        cv_img = self._to_cv2_image(image_input)
        if cv_img is None:
            return []

        results: List[DecodedQRResult] = []

        # 1. Direct multi-detection attempt
        try:
            retval, decoded_info, points, _ = self.detector.detectAndDecodeMulti(cv_img)
            if retval and decoded_info:
                for idx, text in enumerate(decoded_info):
                    if text and text.strip():
                        res = parse_payload(text)
                        if points is not None and idx < len(points):
                            pts = points[idx]
                            res.points = pts
                            res.bounding_box = self._compute_bounding_box(pts)
                        results.append(res)
        except Exception as exc:
            log_error("OpenCV detectAndDecodeMulti", exc)

        # 2. Single detection fallback if multi failed
        if not results:
            try:
                text, points, _ = self.detector.detectAndDecode(cv_img)
                if text and text.strip():
                    res = parse_payload(text)
                    if points is not None:
                        res.points = points
                        res.bounding_box = self._compute_bounding_box(points)
                    results.append(res)
            except Exception as exc:
                log_error("OpenCV detectAndDecode", exc)

        # 3. Adaptive Preprocessing pipelines for noisy/low-contrast images
        if not results:
            results = self._scan_with_preprocessing(cv_img)

        log_scan_event(
            qr_count=len(results),
            file_format="MEMORY/FILE" if not isinstance(image_input, (str, Path)) else Path(image_input).suffix,
        )
        return results

    def _scan_with_preprocessing(self, cv_img: np.ndarray) -> List[DecodedQRResult]:
        """Apply grayscale, contrast stretching, and thresholding to detect difficult QRs."""
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        variants = []
        # Scaled up if small
        if w < 300 or h < 300:
            variants.append(cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC))

        # Otsu thresholding
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(otsu)

        # Adaptive thresholding
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 10
        )
        variants.append(adaptive)

        for candidate in variants:
            try:
                text, points, _ = self.detector.detectAndDecode(candidate)
                if text and text.strip():
                    res = parse_payload(text)
                    if points is not None:
                        res.points = points
                        res.bounding_box = self._compute_bounding_box(points)
                    return [res]
            except Exception:
                continue

        return []

    def _compute_bounding_box(self, points: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Compute (x, y, w, h) bounding box from 4 corner points."""
        try:
            pts = points.reshape(-1, 2)
            x_min = int(np.min(pts[:, 0]))
            y_min = int(np.min(pts[:, 1]))
            x_max = int(np.max(pts[:, 0]))
            y_max = int(np.max(pts[:, 1]))
            return (x_min, y_min, max(0, x_max - x_min), max(0, y_max - y_min))
        except Exception:
            return None

    def scan_clipboard(self) -> List[DecodedQRResult]:
        """Read and decode QR code from image currently copied in system clipboard."""
        try:
            clip_img = ImageGrab.grabclipboard()
            if isinstance(clip_img, Image.Image):
                return self.scan_image(clip_img)
        except Exception as exc:
            log_error("Scanning clipboard image", exc)
        return []

    def scan_screen(
        self,
        bbox: Optional[Tuple[int, int, int, int]] = None,
    ) -> List[DecodedQRResult]:
        """Capture screen (or sub-rectangle) and scan for QR codes."""
        try:
            screenshot = ImageGrab.grab(bbox=bbox)
            return self.scan_image(screenshot)
        except Exception as exc:
            log_error("Scanning screen area", exc)
            return []


class LiveCameraScanner:
    """Manages live webcam stream and real-time QR detection."""

    def __init__(self, camera_index: int = 0) -> None:
        self.camera_index = camera_index
        self.cap: Optional[cv2.VideoCapture] = None
        self.scanner = QRScanner()
        self.is_running = False

    @staticmethod
    def list_available_cameras(max_tested: int = 4) -> List[int]:
        """Detect index of all working webcams on the system."""
        available = []
        for i in range(max_tested):
            temp_cap = cv2.VideoCapture(i, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
            if temp_cap.isOpened():
                available.append(i)
                temp_cap.release()
        return available if available else [0]

    def start(self, camera_index: Optional[int] = None) -> bool:
        """Start the webcam capture stream."""
        if camera_index is not None:
            self.camera_index = camera_index

        self.stop()

        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(self.camera_index, backend)

        if not self.cap.isOpened():
            # Fallback without backend flag
            self.cap = cv2.VideoCapture(self.camera_index)

        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.is_running = True
            return True

        self.is_running = False
        return False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], List[DecodedQRResult]]:
        """Read a frame from camera, detect QR codes, and overlay bounding reticles."""
        if not self.cap or not self.is_running or not self.cap.isOpened():
            return False, None, []

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return False, None, []

        results = self.scanner.scan_image(frame)

        # Draw overlays on detected QR codes
        for res in results:
            if res.points is not None:
                pts = res.points.astype(int).reshape(-1, 2)
                # Draw neon cyan bounding polygon
                cv2.polylines(frame, [pts], isClosed=True, color=(255, 229, 0), thickness=2)
                for pt in pts:
                    cv2.circle(frame, tuple(pt), radius=4, color=(0, 255, 128), thickness=-1)

                # Draw label tag above code
                x, y = pts[0]
                label = f"{res.qr_type.upper()}"
                cv2.putText(
                    frame,
                    label,
                    (x, max(20, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 128),
                    2,
                    cv2.LINE_AA,
                )

        return True, frame, results

    def stop(self) -> None:
        """Release camera resource."""
        self.is_running = False
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
