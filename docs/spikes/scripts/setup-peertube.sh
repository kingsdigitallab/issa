#!/usr/bin/env bash
# Bring up the private, self-hosted PeerTube instance used in the
# archivist-in-the-loop spike. See ../self_hosted_PeerTube.md for the
# recipe this belongs to, and ../verdict-peertube-celluloid.md for the
# exact config this reconstructs.
#
# Run once, manually, on a fresh Linux host with Docker + Compose already
# installed, after a floating IP is assigned. Not idempotent — if a step
# fails partway, fix the cause and re-run rather than assuming a clean
# retry (in particular, re-running will regenerate secrets and overwrite
# the existing .env).
set -euo pipefail

# --- Configuration ------------------------------------------------------
# PT_HOST: the floating IP (or hostname) PeerTube/Caddy will be reachable
# on. Override explicitly: `PT_HOST=1.2.3.4 ./setup-peertube.sh`. Falls
# back to the OpenStack/EC2-compatible instance metadata service, which
# CREATE's cloud supports.
PT_HOST="${PT_HOST:-$(curl -s -m 2 http://169.254.169.254/latest/meta-data/public-ipv4 || true)}"
if [ -z "$PT_HOST" ]; then
  echo "Could not auto-detect a floating IP. Set PT_HOST explicitly." >&2
  exit 1
fi
echo "Using PT_HOST=${PT_HOST}"

PEERTUBE_DIR="${PEERTUBE_DIR:-/opt/peertube}"
SSL_DIR="${SSL_DIR:-/opt/ssl}"
PEERTUBE_REF="${PEERTUBE_REF:-master}"  # branch/tag used in the spike

mkdir -p "$PEERTUBE_DIR" "$SSL_DIR"

# --- 1. Fetch PeerTube's official production docker-compose stack ------
if [ ! -f "$PEERTUBE_DIR/docker-compose.yml" ]; then
  curl -sSL -o "$PEERTUBE_DIR/docker-compose.yml" \
    "https://raw.githubusercontent.com/Chocobozzz/PeerTube/${PEERTUBE_REF}/support/docker/production/docker-compose.yml"
  curl -sSL -o "$PEERTUBE_DIR/.env" \
    "https://raw.githubusercontent.com/Chocobozzz/PeerTube/${PEERTUBE_REF}/support/docker/production/.env"
fi

# --- 2. Apply the .env overrides (see verdict Appendix for the source) -
POSTGRES_PASSWORD="$(openssl rand -hex 24)"
PEERTUBE_SECRET="$(openssl rand -hex 24)"

set_env() {  # set_env KEY VALUE — replace if present, append if not
  local key="$1" value="$2" file="$PEERTUBE_DIR/.env"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    echo "${key}=${value}" >> "$file"
  fi
}

set_env PEERTUBE_WEBSERVER_HOSTNAME "$PT_HOST"
set_env PEERTUBE_WEBSERVER_PORT 443
set_env PEERTUBE_WEBSERVER_HTTPS true
set_env PEERTUBE_SIGNUP_ENABLED false
set_env PEERTUBE_FEDERATION_ENABLED false
set_env PEERTUBE_TRANSCODING_ALWAYS_TRANSCODE_ORIGINAL_RESOLUTION true
set_env PEERTUBE_DEFAULTS_P2P_WEBAPP_ENABLED false
set_env PEERTUBE_DEFAULTS_P2P_EMBED_ENABLED false
set_env POSTGRES_USER peertube
set_env POSTGRES_PASSWORD "$POSTGRES_PASSWORD"
set_env PEERTUBE_SECRET "$PEERTUBE_SECRET"
set_env PEERTUBE_DB_USERNAME peertube
set_env PEERTUBE_DB_PASSWORD "$POSTGRES_PASSWORD"
set_env PEERTUBE_DB_HOSTNAME postgres
set_env PEERTUBE_DB_SSL false
set_env PEERTUBE_TRUST_PROXY '["127.0.0.1", "loopback", "172.28.0.0/16"]'

# --- 3. Edit docker-compose.yml: drop nginx/certbot, expose 9000 -------
# We terminate TLS with Caddy instead of PeerTube's bundled nginx, so the
# webserver/certbot/webserver-reloader services are removed outright
# (equivalent in effect to commenting them out) and the peertube app port
# is published directly for Caddy to reverse-proxy to.
python3 -c "import yaml" 2>/dev/null || pip install --quiet pyyaml
python3 - "$PEERTUBE_DIR/docker-compose.yml" <<'PY'
import sys, yaml
path = sys.argv[1]
with open(path) as f:
    compose = yaml.safe_load(f)
services = compose.get("services", {})
for name in ("webserver", "certbot", "webserver-reloader"):
    services.pop(name, None)
peertube = services.get("peertube", {})
ports = peertube.setdefault("ports", [])
if "9000:9000" not in ports:
    ports.append("9000:9000")
with open(path, "w") as f:
    yaml.safe_dump(compose, f, sort_keys=False)
PY

# --- 4. Self-signed TLS cert (SAN = PT_HOST) for Caddy -----------------
if [ ! -f "$SSL_DIR/peertube.crt" ]; then
  openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
    -keyout "$SSL_DIR/peertube.key" -out "$SSL_DIR/peertube.crt" \
    -subj "/CN=${PT_HOST}" -addext "subjectAltName=IP:${PT_HOST}"
fi

# --- 5. Bring up PeerTube -----------------------------------------------
(cd "$PEERTUBE_DIR" && docker compose up -d)

# --- 6. Caddy: reverse-proxy 443 -> PeerTube's 9000 ---------------------
if ! command -v caddy >/dev/null 2>&1; then
  echo "Caddy isn't installed. Install it (https://caddyserver.com/docs/install)"
  echo "then re-run this script, or start it manually with the Caddyfile below."
fi
cat > "$PEERTUBE_DIR/Caddyfile" <<EOF
:443 {
    tls ${SSL_DIR}/peertube.crt ${SSL_DIR}/peertube.key
    reverse_proxy 127.0.0.1:9000
}
EOF
if command -v caddy >/dev/null 2>&1; then
  caddy start --config "$PEERTUBE_DIR/Caddyfile"
fi

echo
echo "Done. Verify with:"
echo "  curl --cacert ${SSL_DIR}/peertube.crt -sI https://${PT_HOST}"
echo
echo "PeerTube's generated root password:"
(cd "$PEERTUBE_DIR" && docker compose logs peertube | grep -i "user\|password") || true
echo
echo "Remaining steps are manual, in the admin UI (https://${PT_HOST}):"
echo "  - Administration -> Configuration: disable registration, disable"
echo "    federation, transcoding = original resolution only, P2P/WebTorrent off"
echo "  - Create a video channel (e.g. issa_nls)"
