#!/usr/bin/env bash
# Generate the RS256 JWT keypair used by the API for asymmetric token signing.
# Idempotent: existing keys are left untouched unless --force is passed.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRIV="$DIR/jwt_private.pem"
PUB="$DIR/jwt_public.pem"
FORCE="${1:-}"

if [[ -f "$PRIV" && "$FORCE" != "--force" ]]; then
  echo "JWT keys already exist at $DIR (pass --force to regenerate). Skipping."
  exit 0
fi

command -v openssl >/dev/null 2>&1 || { echo "openssl is required but not found." >&2; exit 1; }

echo "Generating RS256 keypair (2048-bit) ..."
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$PRIV" 2>/dev/null
openssl rsa -in "$PRIV" -pubout -out "$PUB" 2>/dev/null

chmod 600 "$PRIV"
chmod 644 "$PUB"

echo "Wrote:"
echo "  $PRIV (private, 0600)"
echo "  $PUB  (public,  0644)"
