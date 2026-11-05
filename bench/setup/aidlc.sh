# Arms 2 and 3: AI-DLC at AIDLC_VERSION, installed offline from the release
# files in the assets, and configured for Claude Code in the project.
: "${BENCH_ASSETS:?the runner copies the assets and sets BENCH_ASSETS}"
. "$BENCH_ASSETS/pins.env"
project="${BENCH_PROJECT_DIR:-/project}"
release="$BENCH_ASSETS/aidlc-release"

if [ "$("$HOME/.local/bin/aidlc" --version 2>/dev/null | cut -d' ' -f2)" != "$AIDLC_VERSION" ]; then
  install_opts=(--from "$release" --version "$AIDLC_VERSION" --quiet --yes)
  # The installer refuses root unless told that root is the container's only user.
  if [ "$(id -u)" = 0 ]; then
    install_opts+=(--allow-root)
  fi
  sh "$release/install.sh" "${install_opts[@]}"
fi
export PATH="$HOME/.local/bin:$PATH"

# Claude Code hands its own environment to AI-DLC's hooks, so aidlc goes on the
# PATH in the file sourced before claude starts. The wrapper in /usr/local/bin
# also puts it on the system PATH that `aidlc doctor` checks.
path_line='export PATH="$HOME/.local/bin:$PATH"'
if ! grep -qxF "$path_line" "$HOME/.claude_env"; then
  echo "$path_line" >> "$HOME/.claude_env"
fi
if [ -w /usr/local/bin ]; then
  printf '#!/bin/sh\nexec %s/.local/bin/aidlc "$@"\n' "$HOME" > /usr/local/bin/aidlc
  chmod 755 /usr/local/bin/aidlc
fi

aidlc config --project-dir "$project" --harness claude --mcp none --quiet
aidlc doctor --project-dir "$project"
