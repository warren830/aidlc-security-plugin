# Arm 3: the security plugin, composed into the project and enabled, in strict
# override mode; the Security Agent MCP server; and the bun and uv they run on.
: "${BENCH_ASSETS:?the runner copies the assets and sets BENCH_ASSETS}"
. "$BENCH_ASSETS/pins.env"
project="${BENCH_PROJECT_DIR:-/project}"

agent_setup="$BENCH_ASSETS/security-agent/config.json"
if [ ! -s "$agent_setup" ]; then
  echo "The assets hold no Security Agent setup: do the one-time setup, then run bench.py setup again." >&2
  exit 1
fi
# The MCP server reads its agent space, role and buckets from here.
install -d -m 700 "$HOME/.securityagent"
install -m 600 "$agent_setup" "$HOME/.securityagent/config.json"

mkdir -p "$HOME/.local/bin"
install -m 755 "$BENCH_ASSETS/bin/bun" "$BENCH_ASSETS/bin/uv" "$BENCH_ASSETS/bin/uvx" "$HOME/.local/bin/"
# Installed now, the server starts from disk when Claude Code launches it.
uv tool install --python 3.12 "$SECURITY_AGENT_MCP"
installed="$(readlink -f "$HOME/.local/bin/${SECURITY_AGENT_MCP%@*}")"
"$installed" --help >/dev/null
# The server uploads a workspace's code to an S3 key named after its path
# alone (scanner.py _workspace_id), and every container works in the same
# path, so parallel runs would overwrite each other's upload and a scan could
# read another task's code. The wrapper salts that key per container and
# changes nothing else.
mcp_server="$HOME/.local/bin/security-agent-mcp-isolated"
cat > "$mcp_server" <<PY
#!$(dirname "$installed")/python
import hashlib
import os

from awslabs.security_agent_mcp_server import scanner, server

salt = os.environ["BENCH_SCAN_SALT"]
scanner.Scanner._workspace_id = staticmethod(
    lambda abs_path: hashlib.md5(f"{salt}:{abs_path}".encode(), usedforsecurity=False).hexdigest()[:12]
)
server.main()
PY
chmod 755 "$mcp_server"

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
# over the Bedrock region the server would inherit from Claude Code, and
# WORKSPACE_ROOT lets it upload the project and nothing outside it.
mcp_env=(-e "AWS_REGION=$SECURITY_AGENT_REGION" -e "WORKSPACE_ROOT=$project" -e "BENCH_SCAN_SALT=$(cat /proc/sys/kernel/random/uuid)")
if [ -n "${AWS_PROFILE:-}" ]; then
  mcp_env+=(-e "AWS_PROFILE=$AWS_PROFILE")
fi
claude mcp remove security-agent --scope local >/dev/null 2>&1 || true
claude mcp add security-agent --scope local "${mcp_env[@]}" -- "$mcp_server"

aidlc engine plugin list
claude mcp get security-agent
