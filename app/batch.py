"""Batch QR Code generator engine for bulk processing CSV and text files."""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from app.generator import QRGenerator
from app.logging_config import log_error
from app.styling import QRStyleConfig


@dataclass
class BatchItem:
    """Individual QR code job in a batch generation queue."""

    index: int
    filename: str
    payload: str
    status: str = "pending"  # "pending", "success", "failed", "skipped"
    error_message: str = ""
    output_path: Optional[Path] = None


class BatchGenerator:
    """Processes multiple QR generation jobs with templates and progress tracking."""

    def __init__(self, style: Optional[QRStyleConfig] = None) -> None:
        self.style = style or QRStyleConfig()
        self.generator = QRGenerator(self.style)

    @staticmethod
    def parse_csv_file(
        file_path: Union[str, Path],
        delimiter: str = ",",
    ) -> Tuple[List[str], List[Dict[str, str]]]:
        """Read CSV file and return (headers, rows)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Auto-detect encoding: try UTF-8 with BOM, UTF-8, then latin1
        content = None
        for enc in ("utf-8-sig", "utf-8", "latin1"):
            try:
                content = path.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            raise ValueError("Unable to decode CSV file with supported encodings.")

        f_io = io.StringIO(content)
        reader = csv.DictReader(f_io, delimiter=delimiter)
        headers = reader.fieldnames or []
        rows = [row for row in reader if any(v.strip() for v in row.values() if v)]
        return list(headers), rows

    @staticmethod
    def parse_text_lines(file_path: Union[str, Path]) -> List[str]:
        """Read text file into non-empty lines."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        for enc in ("utf-8-sig", "utf-8", "latin1"):
            try:
                lines = path.read_text(encoding=enc).splitlines()
                return [line.strip() for line in lines if line.strip()]
            except UnicodeDecodeError:
                continue
        return []

    @staticmethod
    def build_items_from_csv(
        rows: List[Dict[str, str]],
        payload_template: str,
        filename_template: str = "qr_{index}",
    ) -> List[BatchItem]:
        """Transform CSV rows into batch items using curly-brace placeholder templates."""
        items: List[BatchItem] = []
        for idx, row in enumerate(rows, start=1):
            # Safe replacement of placeholders
            payload = payload_template
            filename = filename_template

            for col_name, col_val in row.items():
                if col_name:
                    safe_val = str(col_val or "")
                    payload = payload.replace(f"{{{col_name}}}", safe_val)
                    filename = filename.replace(f"{{{col_name}}}", safe_val)

            # Replace {index} placeholder
            payload = payload.replace("{index}", str(idx))
            filename = filename.replace("{index}", str(idx))

            # Sanitize filename (remove forbidden chars)
            clean_filename = re.sub(r'[\\/*?:"<>|]', "_", filename.strip())
            if not clean_filename:
                clean_filename = f"qr_{idx}"

            items.append(
                BatchItem(
                    index=idx,
                    filename=clean_filename,
                    payload=payload.strip(),
                )
            )
        return items

    @staticmethod
    def build_items_from_lines(
        lines: List[str],
        filename_prefix: str = "qr",
    ) -> List[BatchItem]:
        """Transform list of plain text/URL lines into batch items."""
        items: List[BatchItem] = []
        for idx, line in enumerate(lines, start=1):
            clean_line = line.strip()
            if not clean_line:
                continue
            clean_fn = f"{filename_prefix}_{idx}"
            items.append(
                BatchItem(
                    index=idx,
                    filename=clean_fn,
                    payload=clean_line,
                )
            )
        return items

    def process_batch(
        self,
        items: List[BatchItem],
        output_directory: Union[str, Path],
        file_format: str = "PNG",
        style: Optional[QRStyleConfig] = None,
        progress_callback: Optional[Callable[[int, int, BatchItem], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> List[BatchItem]:
        """Generate all QR codes in batch and save to destination directory."""
        out_dir = Path(output_directory)
        out_dir.mkdir(parents=True, exist_ok=True)

        cfg = style or self.style
        fmt = file_format.upper()
        ext = fmt.lower() if fmt != "JPEG" else "jpg"
        total = len(items)

        for i, item in enumerate(items):
            if cancel_check and cancel_check():
                item.status = "skipped"
                item.error_message = "Batch processing cancelled by user."
                if progress_callback:
                    progress_callback(i + 1, total, item)
                continue

            if not item.payload:
                item.status = "failed"
                item.error_message = "Empty payload."
                if progress_callback:
                    progress_callback(i + 1, total, item)
                continue

            target_file = out_dir / f"{item.filename}.{ext}"

            try:
                self.generator.export_file(
                    payload=item.payload,
                    output_path=target_file,
                    file_format=fmt,
                    style=cfg,
                )
                item.status = "success"
                item.output_path = target_file
            except Exception as exc:
                item.status = "failed"
                item.error_message = str(exc)
                log_error(f"Batch generation for item {item.index}", exc)

            if progress_callback:
                progress_callback(i + 1, total, item)

        return items

    @staticmethod
    def create_zip_archive(source_dir: Union[str, Path], zip_output: Union[str, Path]) -> Path:
        """Package all exported files in source_dir into a zip archive."""
        src = Path(source_dir)
        zip_p = Path(zip_output)
        zip_p.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_p, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in src.rglob("*"):
                if file.is_file() and file != zip_p:
                    zf.write(file, arcname=file.relative_to(src))

        return zip_p
