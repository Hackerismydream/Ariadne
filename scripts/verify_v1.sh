#!/usr/bin/env bash
set -euo pipefail

pytest
ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli ingest examples/sources/*.md
python3.11 -m ariadne_ltb.cli ticket list
python3.11 -m ariadne_ltb.cli workdir cleanup --confirm-cleanup --force-dirty
python3.11 -m ariadne_ltb.cli ticket assign ARI-003 --to fake-codex
python3.11 -m ariadne_ltb.cli daemon run-once
python3.11 -m ariadne_ltb.cli ticket comments ARI-003
python3.11 -m ariadne_ltb.cli runtime journal
python3.11 -m ariadne_ltb.cli runtime recover
python3.11 -m ariadne_ltb.cli daemon status
python3.11 -m ariadne_ltb.cli workdir list
python3.11 -m ariadne_ltb.cli workdir cleanup --confirm-cleanup --force-dirty
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
python3.11 -m ariadne_ltb.cli doctor secrets
python3.11 -m ariadne_ltb.cli doctor store
python3.11 -m ariadne_ltb.cli doctor v1
python3.11 -m ariadne_ltb.cli evidence packet
