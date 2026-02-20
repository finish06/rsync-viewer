from app.services.rsync_parser import RsyncParser, ParsedRsyncOutput


class TestRsyncParserBasic:
    """Test basic parsing functionality"""

    def test_parse_standard_output(self, sample_rsync_output_basic):
        """Test parsing standard rsync output with all fields"""
        result = RsyncParser.parse(sample_rsync_output_basic)

        assert isinstance(result, ParsedRsyncOutput)
        assert result.bytes_sent == int(2.87 * 1024)  # 2.87K
        assert result.bytes_received == int(291.07 * 1024)  # 291.07K
        assert result.transfer_speed == int(117.58 * 1024)  # 117.58K bytes/sec
        assert result.total_size_bytes == int(18.70 * 1024**3)  # 18.70G
        assert result.speedup_ratio == 63.94
        assert result.is_dry_run is False
        assert result.file_count == 5

    def test_parse_returns_parsed_rsync_output(self):
        """Test that parse always returns ParsedRsyncOutput"""
        result = RsyncParser.parse("")
        assert isinstance(result, ParsedRsyncOutput)

    def test_parse_empty_string(self):
        """Test parsing empty string"""
        result = RsyncParser.parse("")

        assert result.total_size_bytes is None
        assert result.bytes_sent is None
        assert result.bytes_received is None
        assert result.transfer_speed is None
        assert result.speedup_ratio is None
        assert result.file_count == 0
        assert result.file_list == []
        assert result.is_dry_run is False


class TestDryRunDetection:
    """Test dry run detection"""

    def test_detect_dry_run(self, sample_rsync_output_dry_run):
        """Test that dry run is detected"""
        result = RsyncParser.parse(sample_rsync_output_dry_run)
        assert result.is_dry_run is True

    def test_detect_dry_run_case_insensitive(self):
        """Test dry run detection is case insensitive"""
        outputs = [
            "total size is 100  speedup is 1.00 (DRY RUN)",
            "total size is 100  speedup is 1.00 (dry run)",
            "total size is 100  speedup is 1.00 (Dry Run)",
        ]
        for output in outputs:
            result = RsyncParser.parse(output)
            assert result.is_dry_run is True

    def test_no_dry_run_marker(self, sample_rsync_output_basic):
        """Test that non-dry run output is correctly identified"""
        result = RsyncParser.parse(sample_rsync_output_basic)
        assert result.is_dry_run is False


class TestByteUnitParsing:
    """Test parsing of various byte units"""

    def test_parse_kilobytes(self, sample_rsync_output_kilobytes):
        """Test parsing kilobyte values"""
        result = RsyncParser.parse(sample_rsync_output_kilobytes)
        assert result.bytes_received == int(5.5 * 1024)  # 5.5K

    def test_parse_terabytes(self, sample_rsync_output_terabytes):
        """Test parsing terabyte values"""
        result = RsyncParser.parse(sample_rsync_output_terabytes)
        assert result.total_size_bytes == int(18.70 * 1024**4)  # 18.70T
        assert result.bytes_received == int(456.78 * 1024**3)  # 456.78G
        assert result.bytes_sent == int(1.23 * 1024**2)  # 1.23M

    def test_parse_bytes_no_unit(self):
        """Test parsing raw byte values without unit suffix"""
        output = "sent 100 bytes  received 200 bytes  300 bytes/sec\ntotal size is 5500  speedup is 1.00"
        result = RsyncParser.parse(output)
        assert result.bytes_sent == 100
        assert result.bytes_received == 200
        assert result.transfer_speed == 300
        assert result.total_size_bytes == 5500

    def test_parse_megabytes(self):
        """Test parsing megabyte values"""
        output = "sent 1.5M bytes  received 2.5M bytes  500K bytes/sec\ntotal size is 100M  speedup is 40.00"
        result = RsyncParser.parse(output)
        assert result.bytes_sent == int(1.5 * 1024**2)
        assert result.bytes_received == int(2.5 * 1024**2)
        assert result.total_size_bytes == int(100 * 1024**2)

    def test_parse_gigabytes(self):
        """Test parsing gigabyte values"""
        output = "sent 1G bytes  received 2.5G bytes  100M bytes/sec\ntotal size is 500G  speedup is 200.00"
        result = RsyncParser.parse(output)
        assert result.bytes_sent == int(1 * 1024**3)
        assert result.bytes_received == int(2.5 * 1024**3)
        assert result.total_size_bytes == int(500 * 1024**3)


class TestFileListExtraction:
    """Test file list extraction"""

    def test_extract_file_list(self, sample_rsync_output_basic):
        """Test that file list is correctly extracted"""
        result = RsyncParser.parse(sample_rsync_output_basic)

        assert result.file_count == 5
        assert "photos/2024/vacation/img_001.jpg" in result.file_list
        assert "photos/2024/vacation/img_002.jpg" in result.file_list
        assert "photos/2024/vacation/img_003.jpg" in result.file_list
        assert "documents/report.pdf" in result.file_list
        assert "backup/database.sql" in result.file_list

    def test_skip_metadata_lines(self, sample_rsync_output_basic):
        """Test that metadata lines are skipped"""
        result = RsyncParser.parse(sample_rsync_output_basic)

        # These should NOT be in the file list
        for item in result.file_list:
            assert not item.lower().startswith("receiving")
            assert not item.lower().startswith("sent ")
            assert not item.lower().startswith("total size")
            assert not item.lower().startswith("done")

    def test_empty_file_list(self, sample_rsync_output_empty):
        """Test parsing output with no files transferred"""
        result = RsyncParser.parse(sample_rsync_output_empty)
        assert result.file_count == 0
        assert result.file_list == []


class TestMalformedInput:
    """Test handling of malformed/edge case input"""

    def test_malformed_output(self, sample_rsync_output_malformed):
        """Test graceful handling of malformed output"""
        result = RsyncParser.parse(sample_rsync_output_malformed)

        # Should return result without crashing
        assert isinstance(result, ParsedRsyncOutput)
        assert result.total_size_bytes is None
        assert result.bytes_sent is None
        assert result.bytes_received is None

    def test_partial_transfer_line(self):
        """Test handling of partial transfer stats"""
        output = "sent 100 bytes  received"  # Incomplete line
        result = RsyncParser.parse(output)
        assert result.bytes_sent is None

    def test_missing_speedup(self):
        """Test handling of missing speedup value"""
        output = "total size is 1.00G"  # Missing speedup
        result = RsyncParser.parse(output)
        assert result.total_size_bytes is None
        assert result.speedup_ratio is None

    def test_numbers_with_commas(self):
        """Test parsing numbers with thousand separators"""
        output = "sent 1,234 bytes  received 5,678 bytes  1,000 bytes/sec\ntotal size is 1,000,000  speedup is 1,234.56"
        result = RsyncParser.parse(output)
        assert result.bytes_sent == 1234
        assert result.bytes_received == 5678
        assert result.transfer_speed == 1000
        assert result.total_size_bytes == 1000000
        assert result.speedup_ratio == 1234.56


class TestUnitMultipliers:
    """Test the unit multiplier values"""

    def test_unit_multiplier_values(self):
        """Verify unit multiplier constants"""
        assert RsyncParser.UNIT_MULTIPLIERS[""] == 1
        assert RsyncParser.UNIT_MULTIPLIERS["K"] == 1024
        assert RsyncParser.UNIT_MULTIPLIERS["M"] == 1024**2
        assert RsyncParser.UNIT_MULTIPLIERS["G"] == 1024**3
        assert RsyncParser.UNIT_MULTIPLIERS["T"] == 1024**4
        assert RsyncParser.UNIT_MULTIPLIERS["P"] == 1024**5

    def test_parse_size_method(self):
        """Test the _parse_size method directly"""
        assert RsyncParser._parse_size("100", "") == 100
        assert RsyncParser._parse_size("1", "K") == 1024
        assert RsyncParser._parse_size("1", "M") == 1024**2
        assert RsyncParser._parse_size("1.5", "G") == int(1.5 * 1024**3)

    def test_parse_number_method(self):
        """Test the _parse_number method directly"""
        assert RsyncParser._parse_number("100") == 100.0
        assert RsyncParser._parse_number("1,234") == 1234.0
        assert RsyncParser._parse_number("1,234,567") == 1234567.0
        assert RsyncParser._parse_number("1.5") == 1.5


class TestFileLineDetection:
    """Test the _is_file_line method"""

    def test_valid_file_paths(self):
        """Test detection of valid file paths"""
        valid_paths = [
            "photos/vacation/img.jpg",
            "documents/report.pdf",
            "/home/user/file.txt",
            "backup.sql",
            "data.json",
        ]
        for path in valid_paths:
            assert RsyncParser._is_file_line(path) is True

    def test_invalid_file_lines(self):
        """Test that metadata lines are not detected as files"""
        invalid_lines = [
            "receiving file list ... done",
            "sent 100 bytes  received 200 bytes",
            "total size is 1.00G  speedup is 1.00",
            "rsync: connection closed",
            "error: connection refused",
            "warning: some warning",
            "done",
            "",
        ]
        for line in invalid_lines:
            assert RsyncParser._is_file_line(line) is False

    def test_empty_line(self):
        """Test that empty lines are not detected as files"""
        assert RsyncParser._is_file_line("") is False
        assert RsyncParser._is_file_line("   ") is False
