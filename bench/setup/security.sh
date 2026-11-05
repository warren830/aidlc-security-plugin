# Arm 3: the security plugin, composed into the project and enabled, in strict
# override mode; the Security Agent MCP server; and the bun and uv they run on.
: "${BENCH_ASSETS:?the runner copies the assets and sets BENCH_ASSETS}"
. "$BENCH_ASSETS/pins.env"
project="${BENCH_PROJECT_DIR:-/project}"

mkdir -p "$HOME/.local/bin"
install -m 755 "$BENCH_ASSETS/bin/bun" "$BENCH_ASSETS/bin/uv" "$BENCH_ASSETS/bin/uvx" "$HOME/.local/bin/"
# Installed now, the server starts from disk when Claude Code launches it.
uv tool install --python 3.12 "$SECURITY_AGENT_MCP"
mcp_server="$HOME/.local/bin/${SECURITY_AGENT_MCP%@*}"
"$mcp_server" --help >/dev/null

cd "$project"
if ! claude plugin marketplace list | grep -q "security-aidlc-plugins"; then
  claude plugin marketplace add "$BENCH_ASSETS/security-plugin"
fi
claude plugin install security@security-aidlc-plugins
aidlc engine plugin sync
aidlc engine plugin select aidlc,security
printf '{"override_mode":"strict"}\n' > .aidlc-security.json

# Local scope keeps the server in this container's ~/.claude.json, so no
# project .mcp.json waits for an approval nobody gives. AWS_REGION here wins
# over the Bedrock region the server would inherit from Claude Code.
mcp_env=(-e "AWS_REGION=$SECURITY_AGENT_REGION")
if [ -n "${AWS_PROFILE:-}" ]; then
  mcp_env+=(-e "AWS_PROFILE=$AWS_PROFILE")
fi
claude mcp remove security-agent --scope local >/dev/null 2>&1 || true
claude mcp add security-agent --scope local "${mcp_env[@]}" -- "$mcp_server"

aidlc engine plugin list
claude mcp get security-agent
