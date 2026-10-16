#!/bin/bash
cd "$(dirname "$0")/.."
python3.10 src/main.py --vfs tests/fixtures/vfs_multiple.zip --script scripts/startup_stage5.txt