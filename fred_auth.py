"""Sign in to FRED's MCP connector once and keep the token for run.py.

The connector (https://mcp.stlouisfed.org) uses OAuth: this script registers
a client, opens the FRED sign-in page in your browser (you accept FRED's terms
there yourself), catches the redirect on localhost, and saves the tokens to
.fred_token.json, which is gitignored. Nothing is printed but the outcome.

    python fred_auth.py            # sign in (first time), then write .mcp.json
    python fred_auth.py --refresh  # renew an expired token and rewrite .mcp.json
"""
import base64
import hashlib
import http.server
import json
import secrets
import sys
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

BASE = "https://mcp.stlouisfed.org"
PORT = 8765
REDIRECT = "http://127.0.0.1:%d/callback" % PORT
HERE = Path(__file__).parent
CLIENT_FILE = HERE / ".fred_client.json"
TOKEN_FILE = HERE / ".fred_token.json"
SCOPE = "mcp:read offline_access"


def post_form(url, data, auth=None):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    if auth:
        req.add_header("Authorization", "Basic " + base64.b64encode(("%s:%s" % auth).encode()).decode())
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def client():
    if CLIENT_FILE.exists():
        return json.loads(CLIENT_FILE.read_text())
    body = json.dumps({"client_name": "FredCheck", "redirect_uris": [REDIRECT],
                       "grant_types": ["authorization_code", "refresh_token"],
                       "response_types": ["code"], "token_endpoint_auth_method": "client_secret_post",
                       "scope": SCOPE}).encode()
    req = urllib.request.Request(BASE + "/register", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        c = json.loads(r.read())
    CLIENT_FILE.write_text(json.dumps(c))
    return c


def save(tok):
    tok["obtained_at"] = int(time.time())
    TOKEN_FILE.write_text(json.dumps(tok))


def sign_in():
    c = client()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    url = BASE + "/authorize?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": c["client_id"], "redirect_uri": REDIRECT,
        "scope": SCOPE, "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
        "resource": BASE + "/"})
    got = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"FredCheck: signed in. You can close this tab.")

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print("Opening FRED sign-in in your browser...")
    webbrowser.open(url)
    while "code" not in got and "error" not in got:
        srv.handle_request()
    if got.get("state") != state or "code" not in got:
        sys.exit("Sign-in failed: %s" % got.get("error", "state mismatch"))
    tok = post_form(BASE + "/token", {
        "grant_type": "authorization_code", "code": got["code"], "redirect_uri": REDIRECT,
        "code_verifier": verifier, "client_id": c["client_id"],
        "client_secret": c.get("client_secret", ""), "resource": BASE + "/"})
    save(tok)
    print("Saved FRED token to %s (gitignored)." % TOKEN_FILE.name)


def refresh():
    c, tok = client(), json.loads(TOKEN_FILE.read_text())
    new = post_form(BASE + "/token", {
        "grant_type": "refresh_token", "refresh_token": tok["refresh_token"],
        "client_id": c["client_id"], "client_secret": c.get("client_secret", "")})
    new.setdefault("refresh_token", tok["refresh_token"])
    save(new)
    print("Refreshed FRED token.")


def access_token():
    """For run.py: a valid access token, refreshing it if it has expired."""
    if not TOKEN_FILE.exists():
        sys.exit("No FRED token yet. Run: python fred_auth.py")
    tok = json.loads(TOKEN_FILE.read_text())
    if time.time() > tok["obtained_at"] + tok.get("expires_in", 3600) - 120:
        refresh()
        tok = json.loads(TOKEN_FILE.read_text())
    return tok["access_token"]


def write_mcp():
    """Write .mcp.json (gitignored) so Claude Code sessions opened in this
    folder get FRED's tools as the 'fred' server. Re-run when the token expires."""
    cfg = {"mcpServers": {"fred": {"type": "http", "url": BASE + "/",
                                   "headers": {"Authorization": "Bearer " + access_token()}}}}
    (HERE / ".mcp.json").write_text(json.dumps(cfg, indent=1))
    print("Wrote .mcp.json for Claude Code (gitignored).")


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        refresh()
    elif not TOKEN_FILE.exists():
        sign_in()
    write_mcp()
