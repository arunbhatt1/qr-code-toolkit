# ⚡ QR Code Toolkit

[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline-emerald.svg)](#-privacy--security-guarantee)
[![Tests](https://img.shields.io/badge/Tests-84%20Passing-brightgreen.svg)](#-running-tests)

A modern, privacy-focused desktop suite for generating, customizing, styling, batch processing, exporting, and scanning QR codes locally with zero external network dependencies. Built with **Python**, **CustomTkinter**, **Pillow**, and **OpenCV**.

---

## ✨ Key Features

### 🎯 1. Interactive Single QR Generator
- **8 Standardized Payload Types**:
  - 🌐 **URL**: Real-time link validation and normalization.
  - 📝 **Plain Text**: Multiline text with live debounced rendering.
  - 📶 **Wi-Fi**: WPA/WPA2/WPA3, WEP, and Open network configurations with ZXing escaping.
  - 👤 **vCard (3.0)**: Contact card with name, company, phone, email, website, and physical address.
  - ✉️ **Email**: `mailto:` with auto-encoded subject and message body.
  - 📞 **Phone**: Standardized `tel:` dialer strings.
  - 💬 **SMS**: `SMSTO:` with phone number and pre-filled message text.
  - 📍 **Geo Location**: `geo:` coordinates with instant Google Maps integration.

### 🎨 2. Style & Customization Studio
- **Curated Color Presets & Custom Hex Pickers**: Classic Dark, Cyber Cyan, Electric Indigo, Emerald Green, Sunset Crimson, Royal Violet, Amber Gold, Slate Modern.
- **Module Shapes**: Square, Rounded (antialiased smooth corners), Circle (dots), and Gapped modules.
- **Error Correction Levels**: Low (7%), Medium (15%), Quartile (25%), and High (30%).
- **Center Logo & Icon Embedding**:
  - Integrates company or brand logos with an automatic protective rounded background shield.
  - Interactive scale slider (10% – 30%).
  - Intelligent safety check threshold to prevent scanning failure.

### 💾 3. Multi-Format High-Res Exporter
- Export to **PNG**, **JPEG**, **SVG** (pure scalable vector XML), and **PDF**.
- **Instant System Clipboard Copy**: Direct native bitmap copy to OS clipboard for instant pasting into Slack, Word, Photoshop, or messaging apps.

### 📷 4. Multi-Source QR Scanner & Live Camera
- **Image File Scanning**: Supports PNG, JPG, BMP, WEBP, TIFF, and GIF.
- **Clipboard Paste**: Decode QR codes copied directly into your clipboard.
- **Screen Capture**: Scan active desktop windows or screen areas.
- **Live Webcam Scanner**: Real-time computer-vision feed with bounding polygon overlays and scan sound/visual cue.
- **Contextual Action Inspector**:
  - "🌐 Open in Web Browser" for URLs.
  - "📋 Copy Wi-Fi Password" for Wi-Fi configurations.
  - "👤 Save as .vcf File" for vCard contacts.
  - "🎨 Send to Generator" to re-style and re-export scanned QR codes.
- **Scan History Log**: Export past scans to CSV or clear history anytime.

### 📦 5. Batch Generation Studio
- Bulk generate hundreds of QR codes from **CSV** or **TXT** files.
- Visual column placeholder templating (e.g., `https://example.com/checkin?id={id}&name={name}`).
- Real-time progress bar, live job log, cancellation control, and automatic **.ZIP** archive packaging.

---

## 🔒 Privacy & Security Guarantee

- 🌐 **100% Local & Offline**: Operates completely disconnected from the internet. No external telemetry, tracking, or cloud servers.
- 🛡️ **Zero Secret Logging**: Passwords, Wi-Fi credentials, contact details, and scan payloads are never recorded in application logs.
- 💻 **Hardware Accelerated & Private**: All image processing and computer vision happen directly on your local CPU.

---

## 🚀 Installation & Quick Start

### Prerequisites
- Python **3.12+**

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/your-username/qr-code-toolkit.git
cd qr-code-toolkit

# Install dependencies
pip install -r requirements.txt

# Or install in development mode with test tools
pip install -r requirements-dev.txt
```

### 2. Run Desktop Application (GUI)
```bash
python -m app.main
```
or
```bash
python -m app.main --gui
```

---

## 💻 CLI Commands (Headless Mode)

The toolkit also includes a fast command-line interface for scripting and automated pipelines:

### Generate QR Code via CLI
```bash
# Generate PNG with custom colors
python -m app.main --generate "https://github.com" --output "github_qr.png" --fg "#6366F1" --bg "#0F172A" --ec "H" --size 500

# Export as Vector SVG
python -m app.main --generate "WIFI:T:WPA;S:OfficeNet;P:Secret123;;" --output "wifi.svg" --format "SVG"

# Export as PDF
python -m app.main --generate "mailto:team@example.com?subject=Hi" --output "contact.pdf" --format "PDF"
```

### Scan QR Code via CLI
```bash
python -m app.main --scan "github_qr.png"
```

---

## 📁 Project Architecture

```
QR Code Toolkit/
├── app/
│   ├── __init__.py            # Version & package metadata
│   ├── main.py                # Application entrypoint & CLI argument router
│   ├── generator.py           # QR generation, drawer styling, logo compositing & exports
│   ├── scanner.py             # OpenCV image decoding, screen grabber & webcam engine
│   ├── batch.py               # Batch processor, CSV templater & zip bundler
│   ├── payloads.py            # Standardized RFC payload formatters
│   ├── styling.py             # Color palettes, module styles, & logo safety calculations
│   ├── validators.py          # Input validation routines for URLs, Wi-Fi, vCard, etc.
│   ├── logging_config.py      # Sanitized, zero-leakage local logging
│   └── gui/
│       ├── __init__.py
│       ├── app.py             # CustomTkinter root window & sidebar navigation
│       ├── components.py      # Reusable widgets, color pickers, status badges, toasts
│       ├── generator_view.py  # Single QR studio with live real-time preview
│       ├── scanner_view.py    # Scanner studio (Image, Screen, Webcam feed)
│       ├── batch_view.py      # Bulk CSV/TXT batch generator
│       └── settings_view.py   # Theme switcher, privacy log viewer & diagnostics
├── tests/                     # 84 automated unit & integration tests
│   ├── test_validators.py
│   ├── test_payloads.py
│   ├── test_styling.py
│   ├── test_generator.py
│   ├── test_scanner.py
│   ├── test_batch.py
│   ├── test_logging.py
│   ├── test_main.py
│   └── test_gui.py
├── pyproject.toml             # Project configuration & test dependencies
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development & test tools
└── README.md                  # Complete documentation
```

---

## 🧪 Running Tests

Execute the complete automated test suite with coverage report:

```bash
python -m pytest -v --cov=app --cov-report=term-missing
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
