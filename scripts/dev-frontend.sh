#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../frontend"

npm i
npm run dev
