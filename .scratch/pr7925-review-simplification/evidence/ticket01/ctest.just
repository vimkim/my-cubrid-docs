set shell := ["bash", "-eu", "-c"]

# Filtered form of the live core::ctest recipe, retaining its preflight and lock.
[working-directory("/home/vimkim/gh/cb/pr7925-01-stored-rows")]
selected pattern:
    #!/usr/bin/env bash
    set -euo pipefail
    bash "${MY_CUBRID:-$HOME/my-cubrid}/bin/cubrid-test-socket-preflight.sh"
    "${MY_CUBRID:-$HOME/my-cubrid}/bin/cubrid-build-coordinator.sh" installation-use 300 -- ctest --test-dir "$CUBRID_BUILD_DIR" --output-on-failure --verbose -R '{{pattern}}'
