#!/usr/bin/env bash
# Register the L9 box's durable credentials in Infisical (project Cursor-Governance).
#
# Runs on the operator's machine. Reads the box over SSH (read-only: one tar stream of specific
# files plus one `docker inspect`), copies each value into a mode-700 temporary directory, upserts it
# by name, verifies it by hash, and deletes the directory on exit. A value never appears in argv, in
# the terminal, or on disk outside that directory.
#
#   register_box_secrets.sh              # collect, upload, verify
#   register_box_secrets.sh --dry-run    # collect and print the plan; upload nothing
#   register_box_secrets.sh --no-verify  # skip the read-back hash check
#
# Environment:
#   L9_BOX_HOST           default root@167.233.222.27
#   L9_BOX_KEY            default ~/.ssh/l9_box_ed25519   (also the key that gets registered)
#   INFISICAL_ENV         default prod
#   INFISICAL_PATH        default /
#   INFISICAL_PROJECT_ID  default the Cursor-Governance project id from the inventory
#   INFISICAL_TOKEN       optional machine-identity token; otherwise the CLI session is used
#
# Requires: ssh, tar, and the Infisical CLI (brew install infisical/get-cli/infisical), already
# authenticated (`infisical login`, or `infisical login --method=universal-auth --client-id=...
# --client-secret=...`). Verified against CLI 0.43.84: that release has no `secrets-manager`
# command, and `secrets set` is an upsert, so re-running this script is safe.
set -euo pipefail

BOX_HOST=${L9_BOX_HOST:-root@167.233.222.27}
BOX_KEY=${L9_BOX_KEY:-$HOME/.ssh/l9_box_ed25519}
INFISICAL_ENV=${INFISICAL_ENV:-prod}
INFISICAL_PATH=${INFISICAL_PATH:-/}
INFISICAL_PROJECT_ID=${INFISICAL_PROJECT_ID:-9f92179d-3caa-4d7a-90a9-bb896499bfe6}
DRY_RUN=0
VERIFY=1

# Remote files, relative to /, copied in one stream. Everything else is derived from these.
REMOTE_PATHS="etc/l9/governance.token
root/.ssh/github_deploy
root/.ssh/id_ivx_tunnel
home/l9/.ssh/l9_split
home/l9/.ssh/l9_cog
home/l9/.ssh/l9_ops
home/l9/apps/splitwisely/.env"
# Collapsed to one line: a newline-separated list would become separate commands on the remote shell.
REMOTE_LIST=$(printf '%s' "$REMOTE_PATHS" | tr '\n' ' ')

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}
note() { printf '%s\n' "$*" >&2; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --no-verify) VERIFY=0 ;;
    -h | --help)
      # Print the header comment only: stop at the first line that is not a comment, so adding a
      # line to the header can never leak code into --help.
      awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "$0"
      exit 0
      ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

command -v ssh >/dev/null 2>&1 || die "ssh not found"
command -v tar >/dev/null 2>&1 || die "tar not found"
command -v infisical >/dev/null 2>&1 ||
  die "infisical CLI not found: brew install infisical/get-cli/infisical"
[ -f "$BOX_KEY" ] || die "box key not found: $BOX_KEY (set L9_BOX_KEY to the key that logs in as root)"

if command -v sha256sum >/dev/null 2>&1; then
  sha() { sha256sum | awk '{print $1}'; }
else
  sha() { shasum -a 256 | awk '{print $1}'; }
fi

umask 077
work=$(mktemp -d "${TMPDIR:-/tmp}/l9-register-secrets.XXXXXX")
cleanup() { rm -rf "$work"; }
trap cleanup EXIT
trap 'cleanup; exit 130' INT
trap 'cleanup; exit 143' TERM
mkdir -p "$work/src" "$work/out"

ssh_box() {
  ssh -i "$BOX_KEY" \
    -o IdentitiesOnly=yes \
    -o StrictHostKeyChecking=accept-new \
    -o ConnectTimeout=15 \
    "$BOX_HOST" "$@"
}

# Bash 3.2 (the macOS default) treats "${empty[@]}" as unbound under set -u, so arrays are only
# expanded through the ${arr[@]+...} idiom.
token_args=()
if [ -n "${INFISICAL_TOKEN:-}" ]; then
  token_args=(--token "$INFISICAL_TOKEN")
fi
infisical_() {
  infisical "$@" ${token_args[@]+"${token_args[@]}"}
}

NAMES=()
SOURCES=()
SKIPPED=()
skipped_count=0
register() { # register <name> <source-file> <source-description>
  chmod 600 "$2"
  cp "$2" "$work/out/$1"
  chmod 600 "$work/out/$1"
  NAMES+=("$1")
  SOURCES+=("$3")
}

note "== preflight"
ssh_box 'true' || die "cannot ssh to $BOX_HOST with $BOX_KEY"
# One round trip: list every missing path at once instead of opening a connection per file.
missing=$(ssh_box "cd / && for p in $REMOTE_LIST; do [ -e \"\$p\" ] || echo \"\$p\"; done") ||
  die "failed to inspect $BOX_HOST"
[ -z "$missing" ] || die "missing on the box: $(printf '%s' "$missing" | tr '\n' ' ')"
ssh_box 'docker inspect splitwisely-mysql >/dev/null 2>&1' ||
  die "container splitwisely-mysql not found; cannot read MYSQL_ROOT_PASSWORD"

if [ "$DRY_RUN" -eq 0 ]; then
  infisical_ secrets --env "$INFISICAL_ENV" --path "$INFISICAL_PATH" \
    --projectId "$INFISICAL_PROJECT_ID" --silent -o json >/dev/null 2>"$work/auth.err" ||
    die "infisical is not authenticated for project $INFISICAL_PROJECT_ID:
$(cat "$work/auth.err")
log in with: infisical login
  or:        infisical login --method=universal-auth --client-id=... --client-secret=..."
fi

note "== collect"
# One tar stream keeps every byte exact and keeps values out of any shell quoting on the remote side.
# shellcheck disable=SC2086
ssh_box "tar -C / -cf - $REMOTE_LIST" | tar -C "$work/src" -xf - ||
  die "failed to copy files from $BOX_HOST"

# The root login key is local: it is the credential this script authenticates with.
register L9_BOX_ROOT_SSH_PRIVATE_KEY_ED25519 "$BOX_KEY" "local $BOX_KEY"

# The bearer token is 64 hex characters; the file's trailing newline is not part of the value.
tr -d '\n\r' <"$work/src/etc/l9/governance.token" >"$work/token"
register L9_BOX_GOVERNANCE_BEARER_TOKEN "$work/token" "/etc/l9/governance.token"

register_file() { # register_file <name> <path-relative-to-root>
  register "$1" "$work/src/$2" "/$2"
}
register_file L9_DEPLOY_KEY_IGORBOT root/.ssh/github_deploy
register_file L9_TUNNEL_SSH_PRIVATE_KEY root/.ssh/id_ivx_tunnel
register_file L9_DEPLOY_KEY_SPLITWISELY home/l9/.ssh/l9_split
register_file L9_DEPLOY_KEY_COGNITIVE_RUNTIME home/l9/.ssh/l9_cog
register_file L9_DEPLOY_KEY_L9_OPS home/l9/.ssh/l9_ops

ssh_box 'docker inspect splitwisely-mysql --format "{{range .Config.Env}}{{println .}}{{end}}"' |
  sed -n 's/^MYSQL_ROOT_PASSWORD=//p' >"$work/mysql"
[ -s "$work/mysql" ] || die "MYSQL_ROOT_PASSWORD is empty in the splitwisely-mysql container"
register SPLITWISELY_MYSQL_ROOT_PASSWORD "$work/mysql" \
  "docker inspect splitwisely-mysql (MYSQL_ROOT_PASSWORD)"

# Every key in the service's .env is registered as SPLITWISELY_<KEY>: partial vaulting is what leaves
# a redeploy broken six months later. Quotes are stripped the way dotenv reads them.
env_file="$work/src/home/l9/apps/splitwisely/.env"
env_count=0
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in '' | '#'*) continue ;; esac
  case "$line" in *=*) : ;; *) continue ;; esac
  key=${line%%=*}
  case "$key" in *[!A-Za-z0-9_]*) continue ;; esac
  value=${line#*=}
  value=${value%$'\r'}
  case "$value" in
    \"*\") value=${value#\"}; value=${value%\"} ;;
    \'*\') value=${value#\'}; value=${value%\'} ;;
  esac
  # A key present with an empty value is an unconfigured integration, not a secret. Storing "" would
  # make the vault claim a credential exists, so it is reported instead of uploaded.
  if [ -z "$value" ]; then
    SKIPPED+=("SPLITWISELY_$key")
    skipped_count=$((skipped_count + 1))
    env_count=$((env_count + 1))
    continue
  fi
  printf '%s' "$value" >"$work/env_$key"
  register "SPLITWISELY_$key" "$work/env_$key" "/home/l9/apps/splitwisely/.env"
  env_count=$((env_count + 1))
done <"$env_file"
[ "$env_count" -eq 17 ] || note "warning: expected 17 SplitWisely keys, found $env_count"

total=${#NAMES[@]}
[ "$total" -gt 0 ] || die "nothing collected"

note "== plan: $total secrets -> project $INFISICAL_PROJECT_ID, env $INFISICAL_ENV, path $INFISICAL_PATH"
printf '%-46s %9s  %s\n' NAME BYTES SOURCE
i=0
while [ "$i" -lt "$total" ]; do
  printf '%-46s %9s  %s\n' "${NAMES[$i]}" \
    "$(wc -c <"$work/out/${NAMES[$i]}" | tr -d ' ')" "${SOURCES[$i]}"
  i=$((i + 1))
done

if [ "$skipped_count" -gt 0 ]; then
  note "== skipped: $skipped_count keys are present but empty on the box (unconfigured, not uploaded)"
  for name in ${SKIPPED[@]+"${SKIPPED[@]}"}; do
    printf '  empty %s\n' "$name" >&2
  done
fi

if [ "$DRY_RUN" -eq 1 ]; then
  note "dry run: nothing uploaded"
  exit 0
fi

note "== upload"
i=0
while [ "$i" -lt "$total" ]; do
  name=${NAMES[$i]}
  if ! infisical_ secrets set "$name=@$work/out/$name" \
    --env "$INFISICAL_ENV" \
    --path "$INFISICAL_PATH" \
    --projectId "$INFISICAL_PROJECT_ID" \
    --expand=false \
    --silent >/dev/null; then
    die "failed to set $name"
  fi
  printf '  set %s\n' "$name"
  i=$((i + 1))
done

if [ "$VERIFY" -eq 0 ]; then
  note "upload complete: $total secrets (verification skipped)"
  exit 0
fi

note "== verify: every name reads back with a hash-equal value (nothing is printed)"
# Each name is read individually. The listing (`secrets -o json`) marshals the v3 model as
# secretKey/secretValue, so matching a name inside it would test the JSON shape, not the secret;
# a failed `secrets get` is the one unambiguous statement that the name is not there.
failures=0
i=0
while [ "$i" -lt "$total" ]; do
  name=${NAMES[$i]}
  if ! stored=$(infisical_ secrets get "$name" \
    --env "$INFISICAL_ENV" --path "$INFISICAL_PATH" \
    --projectId "$INFISICAL_PROJECT_ID" --expand=false --plain --silent 2>/dev/null); then
    printf '  MISSING %s\n' "$name" >&2
    failures=$((failures + 1))
    i=$((i + 1))
    continue
  fi
  # Command substitution strips trailing newlines on both sides, so a value that ends in one still matches.
  expected=$(printf '%s' "$(cat "$work/out/$name")" | sha)
  actual=$(printf '%s' "$stored" | sha)
  if [ "$expected" != "$actual" ]; then
    printf '  MISMATCH %s\n' "$name" >&2
    failures=$((failures + 1))
  fi
  i=$((i + 1))
done
[ "$failures" -eq 0 ] || die "$failures of $total secrets failed verification"
note "verified: $total secrets match their source values; $skipped_count empty keys skipped"
