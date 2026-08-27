"""Main application entry point with CLI arguments and GUI launcher."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app import __version__
from app.logging_config import get_logger, log_error, setup_logging


def build_cli_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="qr-toolkit",
        description="QR Code Toolkit - Privacy-focused desktop generator and scanner.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the desktop graphical interface (default).",
    )
    parser.add_argument(
        "--generate",
        metavar="PAYLOAD",
        type=str,
        help="Generate a QR code from the command line.",
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="PATH",
        type=str,
        default="qrcode.png",
        help="Output destination path for generated QR code (default: qrcode.png).",
    )
    parser.add_argument(
        "--format",
        choices=["PNG", "JPG", "SVG", "PDF"],
        default="PNG",
        help="File format for generated QR code (default: PNG).",
    )
    parser.add_argument(
        "--fg",
        metavar="HEX",
        default="#000000",
        help="Foreground module color in hex (default: #000000).",
    )
    parser.add_argument(
        "--bg",
        metavar="HEX",
        default="#FFFFFF",
        help="Background canvas color in hex (default: #FFFFFF).",
    )
    parser.add_argument(
        "--ec",
        choices=["L", "M", "Q", "H"],
        default="M",
        help="Error correction level (default: M).",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=400,
        help="Pixel resolution / size of generated QR code (default: 400).",
    )
    parser.add_argument(
        "--scan",
        metavar="IMAGE_PATH",
        type=str,
        help="Scan and decode QR code from an image file.",
    )
    return parser


def handle_cli_generate(args: argparse.Namespace) -> int:
    """Execute command-line QR code generation."""
    if not args.generate or not args.generate.strip():
        print("❌ Error: QR code payload cannot be empty.", file=sys.stderr)
        return 1

    from app.generator import QRGenerator
    from app.styling import QRStyleConfig

    cfg = QRStyleConfig(
        fg_color=args.fg,
        bg_color=args.bg,
        error_correction=args.ec,
        custom_size=args.size,
    )
    gen = QRGenerator(cfg)
    out_path = Path(args.output)

    try:
        saved = gen.export_file(
            payload=args.generate,
            output_path=out_path,
            file_format=args.format,
            style=cfg,
            target_size=args.size,
        )
        print(f"✅ Successfully generated QR code: {saved.resolve()}")
        return 0
    except Exception as exc:
        print(f"❌ Error generating QR code: {exc}", file=sys.stderr)
        log_error("CLI generate", exc)
        return 1


def handle_cli_scan(args: argparse.Namespace) -> int:
    """Execute command-line QR code scanning."""
    from app.scanner import QRScanner

    scanner = QRScanner()
    img_path = Path(args.scan)

    if not img_path.exists():
        print(f"❌ Error: File not found at '{img_path}'", file=sys.stderr)
        return 1

    try:
        results = scanner.scan_image(img_path)
        if not results:
            print(f"⚠️ No QR codes detected in '{img_path}'.")
            return 1

        print(f"🔍 Detected {len(results)} QR code(s):\n" + "=" * 50)
        for i, res in enumerate(results, 1):
            print(f"[{i}] Type: {res.qr_type.upper()}")
            if res.parsed_data:
                for k, v in res.parsed_data.items():
                    print(f"    • {k}: {v}")
            print(f"    • Raw Payload: {res.raw_text}")
            print("-" * 50)
        return 0
    except Exception as exc:
        print(f"❌ Error during scan: {exc}", file=sys.stderr)
        log_error("CLI scan", exc)
        return 1


def main() -> None:
    """Main entrypoint routing to CLI tasks or launching GUI."""
    setup_logging()
    parser = build_cli_parser()
    args = parser.parse_args()

    if args.generate:
        sys.exit(handle_cli_generate(args))
    elif args.scan:
        sys.exit(handle_cli_scan(args))
    else:
        # Default: Launch GUI
        try:
            from app.gui.app import run_app

            run_app()
        except Exception as exc:
            log_error("Launching desktop GUI", exc)
            print(f"❌ Error launching GUI: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
