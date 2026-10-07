set shell := ["bash", "-eu", "-c"]

# Evidence-only filtered form of the live core::ctest recipe.
[working-directory("/home/vimkim/gh/cb/pr7925-02-record-owner")]
selected pattern:
    #!/usr/bin/env bash
    set -euo pipefail
    bash "${MY_CUBRID:-$HOME/my-cubrid}/bin/cubrid-test-socket-preflight.sh"
    "${MY_CUBRID:-$HOME/my-cubrid}/bin/cubrid-build-coordinator.sh" installation-use 300 -- ctest --test-dir "$CUBRID_BUILD_DIR" --output-on-failure --verbose -R '{{pattern}}'
