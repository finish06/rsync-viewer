import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedRsyncOutput:
    total_size_bytes: Optional[int] = None
    bytes_sent: Optional[int] = None
    bytes_received: Optional[int] = None
    transfer_speed: Optional[float] = None
    speedup_ratio: Optional[float] = None
    file_list: list[str] = field(default_factory=list)
    file_count: int = 0
    is_dry_run: bool = False


class RsyncParser:
    # Pattern: "sent 2.87K bytes  received 291.07K bytes  117.58K bytes/sec"
    TRANSFER_PATTERN = re.compile(
        r"sent\s+([\d.,]+)([KMGTP]?)\s*bytes\s+"
        r"received\s+([\d.,]+)([KMGTP]?)\s*bytes\s+"
        r"([\d.,]+)([KMGTP]?)\s*bytes/sec",
        re.IGNORECASE,
    )

    # Pattern: "total size is 18.70T  speedup is 63,604,231.94"
    TOTAL_SIZE_PATTERN = re.compile(
        r"total\s+size\s+is\s+([\d.,]+)([KMGTP]?)\s+" r"speedup\s+is\s+([\d.,]+)",
        re.IGNORECASE,
    )

    UNIT_MULTIPLIERS = {
        "": 1,
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
        "P": 1024**5,
    }

    # Lines to skip when extracting file list
    SKIP_PREFIXES = (
        "starting",
        "pid",
        "beginning",
        "receiving file list",
        "building file list",
        "sent ",
        "total size",
        "rsync",
        "error",
        "warning",
        "done",
    )

    @classmethod
    def parse(cls, raw_content: str) -> ParsedRsyncOutput:
        result = ParsedRsyncOutput()

        # Parse transfer stats
        transfer_match = cls.TRANSFER_PATTERN.search(raw_content)
        if transfer_match:
            result.bytes_sent = cls._parse_size(
                transfer_match.group(1), transfer_match.group(2)
            )
            result.bytes_received = cls._parse_size(
                transfer_match.group(3), transfer_match.group(4)
            )
            result.transfer_speed = cls._parse_size(
                transfer_match.group(5), transfer_match.group(6)
            )

        # Parse total size and speedup
        total_match = cls.TOTAL_SIZE_PATTERN.search(raw_content)
        if total_match:
            result.total_size_bytes = cls._parse_size(
                total_match.group(1), total_match.group(2)
            )
            result.speedup_ratio = cls._parse_number(total_match.group(3))

        # Detect dry run
        result.is_dry_run = "(DRY RUN)" in raw_content.upper()

        # Extract file list
        for line in raw_content.split("\n"):
            line = line.strip()
            if cls._is_file_line(line):
                result.file_list.append(line)

        result.file_count = len(result.file_list)

        return result

    @classmethod
    def _parse_size(cls, value: str, unit: str) -> int:
        number = cls._parse_number(value)
        multiplier = cls.UNIT_MULTIPLIERS.get(unit.upper(), 1)
        return int(number * multiplier)

    @classmethod
    def _parse_number(cls, value: str) -> float:
        return float(value.replace(",", ""))

    @classmethod
    def _is_file_line(cls, line: str) -> bool:
        if not line:
            return False
        lower_line = line.lower()
        if any(lower_line.startswith(prefix) for prefix in cls.SKIP_PREFIXES):
            return False
        # Must contain a path separator or file extension
        return "/" in line or ("." in line and len(line.split(".")[-1]) <= 5)
