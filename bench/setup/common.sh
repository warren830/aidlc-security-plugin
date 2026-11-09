# Every arm: Node.js 22 and the pinned Claude Code, as upstream SusVibes
# setup-env.sh installs them, without ANTHROPIC_MODEL (the agent env sets it).
: "${CLAUDE_CODE_VERSION:?the runner passes CLAUDE_CODE_VERSION}"

node_major() { node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0; }

if [ "$(node_major)" -lt 22 ]; then
  if ! command -v curl >/dev/null 2>&1; then
    apt-get update
    apt-get install -y curl ca-certificates
  fi
  export NVM_DIR="$HOME/.nvm"
  if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash
  fi
  set +u # nvm.sh reads unset variables
  . "$NVM_DIR/nvm.sh"
  nvm install 22
  set -u
fi

npm_bin="$(npm prefix -g)/bin"
export PATH="$npm_bin:$PATH"
if [ "$(claude --version 2>/dev/null | cut -d' ' -f1)" != "$CLAUDE_CODE_VERSION" ]; then
  npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"
fi

# Every command the runner starts in the container sources this file. The
# auto-updater would move Claude Code off the pinned version during a run.
cat > "$HOME/.claude_env" <<EOF
export FORCE_AUTO_BACKGROUND_TASKS="1"
export ENABLE_BACKGROUND_TASKS="1"
export DISABLE_AUTOUPDATER="1"
export PATH="$npm_bin:\$PATH"
EOF
if ! grep -qxF "source $HOME/.claude_env" "$HOME/.bashrc" 2>/dev/null; then
  echo "source $HOME/.claude_env" >> "$HOME/.bashrc"
fi

installed="$(claude --version)"
echo "claude --version: $installed"
[ "${installed%% *}" = "$CLAUDE_CODE_VERSION" ]
