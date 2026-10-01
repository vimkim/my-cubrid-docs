"""Verify the parser defect offline using retained CI output, without a database."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
for name, expected in [("wrong-password-output.txt", 0), ("changed-password-output.txt", 2)]:
    text = (root / name).read_text()
    def count(pattern, value, whole_word=False):
        args = ["grep", "-wc" if whole_word else "-Ec", pattern]
        result = subprocess.run(args, input=value, text=True, capture_output=True)
        assert result.returncode in (0, 1), result.stderr
        return int(result.stdout)
    old = count("100", text, True)
    rows = count(r"^[[:space:]]*100[[:space:]]*$", text)
    changed_ip = count("100", text.replace("10.233.111.100", "10.233.111.101"), True)
    assert (old, rows, changed_ip) == (3, expected, expected)
    print(f"{name}: original grep={old}; numeric rows={rows}; changed IP grep={changed_ip}; expected={expected}")
print("PASS: both false failure counts reproduced; no database or testcase rerun")
