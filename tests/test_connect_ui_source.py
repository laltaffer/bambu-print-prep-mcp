import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from bambu_print_prep_mcp import submission


@pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("swift"), reason="macOS Swift")
def test_native_review_parser_with_no_app_access(tmp_path):
    source = Path(submission.__file__).with_name("connect_ui.swift")
    harness = Path(__file__).with_name("connect_ui_fixtures.swift")
    combined = tmp_path / "native-review-fixtures.swift"
    combined.write_text(source.read_text() + "\n" + harness.read_text())
    result = subprocess.run(
        [
            "/usr/bin/swift",
            "-D",
            "AX_FIXTURES",
            "-module-cache-path",
            str(tmp_path / "module-cache"),
            str(combined),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "no app accessed" in result.stdout
