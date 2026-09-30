#!/usr/bin/env bash
set -euo pipefail

mode="${1:---offline}"
case "$mode" in
  --offline)
    export RUN_LIVE=0
    export RUN_LIVE_NOTEBOOK=0
    ;;
  --live)
    export RUN_LIVE=1
    export RUN_LIVE_NOTEBOOK=1
    ;;
  *)
    echo "Usage: ./run_notebook.sh [--offline|--live]" >&2
    exit 2
    ;;
esac

jupyter nbconvert --to notebook --execute property_profiles.ipynb \
  --output property_profiles.ipynb \
  --ExecutePreprocessor.timeout=600
