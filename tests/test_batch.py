"""Unit tests for batch QR code generation."""

from pathlib import Path

from app.batch import BatchGenerator, BatchItem
from app.styling import QRStyleConfig


class TestBatchGenerator:
    """Test suite for CSV/TXT parsing, templating, and bulk export."""

    def test_parse_csv_file(self, tmp_path: Path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("id,name,url\n1,Alice,https://alice.com\n2,Bob,https://bob.com\n", encoding="utf-8")

        headers, rows = BatchGenerator.parse_csv_file(csv_file)
        assert headers == ["id", "name", "url"]
        assert len(rows) == 2
        assert rows[0]["name"] == "Alice"
        assert rows[1]["url"] == "https://bob.com"

    def test_build_items_from_csv(self):
        rows = [
            {"id": "101", "name": "Alice"},
            {"id": "102", "name": "Bob"},
        ]
        items = BatchGenerator.build_items_from_csv(
            rows=rows,
            payload_template="https://app.io/user?id={id}&name={name}",
            filename_template="badge_{id}_{name}",
        )
        assert len(items) == 2
        assert items[0].filename == "badge_101_Alice"
        assert items[0].payload == "https://app.io/user?id=101&name=Alice"
        assert items[1].filename == "badge_102_Bob"

    def test_process_batch_generation(self, tmp_path: Path):
        out_dir = tmp_path / "output_qr"
        items = [
            BatchItem(index=1, filename="qr_1", payload="https://one.com"),
            BatchItem(index=2, filename="qr_2", payload="https://two.com"),
        ]

        engine = BatchGenerator()
        results = engine.process_batch(
            items=items,
            output_directory=out_dir,
            file_format="PNG",
        )

        assert len(results) == 2
        assert all(r.status == "success" for r in results)
        assert (out_dir / "qr_1.png").exists()
        assert (out_dir / "qr_2.png").exists()

    def test_create_zip_archive(self, tmp_path: Path):
        out_dir = tmp_path / "qr_folder"
        out_dir.mkdir()
        (out_dir / "test.png").write_bytes(b"mock_png_data")

        zip_dest = tmp_path / "archive.zip"
        saved_zip = BatchGenerator.create_zip_archive(out_dir, zip_dest)

        assert saved_zip.exists()
        assert saved_zip.stat().st_size > 0

    def test_parse_text_lines(self, tmp_path: Path):
        txt_file = tmp_path / "urls.txt"
        txt_file.write_text("https://one.com\nhttps://two.com\n\nhttps://three.com\n", encoding="utf-8")

        lines = BatchGenerator.parse_text_lines(txt_file)
        assert len(lines) == 3
        assert lines[0] == "https://one.com"
        assert lines[2] == "https://three.com"

    def test_build_items_from_lines(self):
        lines = ["https://apple.com", "https://google.com"]
        items = BatchGenerator.build_items_from_lines(lines, filename_prefix="site")
        assert len(items) == 2
        assert items[0].filename == "site_1"
        assert items[0].payload == "https://apple.com"

    def test_batch_cancellation(self, tmp_path: Path):
        out_dir = tmp_path / "out_cancel"
        items = [
            BatchItem(index=1, filename="qr_1", payload="https://one.com"),
            BatchItem(index=2, filename="qr_2", payload="https://two.com"),
        ]

        engine = BatchGenerator()
        # Cancel immediately
        results = engine.process_batch(
            items=items,
            output_directory=out_dir,
            cancel_check=lambda: True,
        )
        assert all(r.status == "skipped" for r in results)

