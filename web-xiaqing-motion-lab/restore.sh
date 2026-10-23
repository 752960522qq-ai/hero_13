#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
cat source.tar.gz.part* | tar -xz
