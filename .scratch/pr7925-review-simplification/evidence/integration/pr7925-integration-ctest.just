set shell := ["bash", "-eu", "-c"]

# Filtered live core::ctest recipe with the same socket preflight and lock.
[working-directory("/home/vimkim/gh/cb/pr7925-simplification-integration")]
selected pattern:
    #!/usr/bin/env bash
    set -euo pipefail
    bash "${MY_CUBRID:-$HOME/my-cubrid}/bin/cubrid-test-socket-preflight.sh"
    "${MY_CUBRID:-$HOME/my-cubrid}/bin/cubrid-build-coordinator.sh" installation-use 300 -- ctest --test-dir "$CUBRID_BUILD_DIR" --output-on-failure --verbose -R '{{pattern}}'
