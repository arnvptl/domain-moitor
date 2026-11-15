import json
import os
import smtplib
import sys
import urllib.request
import urllib.error
from email.message import EmailMessage

DOMAIN = os.getenv("DOMAIN", "panipuri.cfd").strip().lower()
SPACESHIP_API_KEY = os.environ["SPACESHIP_API_KEY"]
SPACESHIP_API_SECRET = os.environ["SPACESHIP_API_SECRET"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]
ALERT_SENT = os.getenv("ALERT_SENT", "false").lower() == "true"

def request_json(url, method="GET", headers=None, body=None):
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"detail": raw[:500]}
        return exc.code, payload

def spaceship_availability():
    # Spaceship's documented single-domain availability endpoint.
    url = f"https://spaceship.dev/api/v1/domains/{DOMAIN}/available"
    headers = {
        "X-API-Key": SPACESHIP_API_KEY,
        "X-API-Secret": SPACESHIP_API_SECRET,
        "Accept": "application/json",
    }
    status, payload = request_json(url, headers=headers)
    if status != 200:
        raise RuntimeError(f"Spaceship API returned HTTP {status}: {payload}")
    result = str(payload.get("result", "")).lower()
    if result not in {"available", "unavailable"}:
        raise RuntimeError(f"Unexpected Spaceship response: {payload}")
    return result == "available", payload

def rdap_status():
    # Discover the authoritative RDAP service for the TLD using IANA bootstrap.
    _, bootstrap = request_json("https://data.iana.org/rdap/dns.json")
    tld = DOMAIN.rsplit(".", 1)[-1]
    base = None
    for suffixes, urls in bootstrap.get("services", []):
        if tld in suffixes:
            base = urls[0]
            break
    if not base:
        return "No RDAP service listed by IANA for this TLD"
    url = base.rstrip("/") + "/domain/" + DOMAIN
    req = urllib.request.Request(url, headers={"Accept": "application/rdap+json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return f"Registered record returned (HTTP {response.status})"
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "RDAP returned 404 (no current registration record; not proof of retail availability)"
        return f"RDAP HTTP {exc.code}"

def send_email(rdap):
    sender = os.environ["EMAIL_ADDRESS"]
    recipient = os.environ["NOTIFY_EMAIL"]
    password = os.environ["GMAIL_APP_PASSWORD"]

    msg = EmailMessage()
    msg["Subject"] = f"DOMAIN AVAILABLE: {DOMAIN}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        f"Spaceship reports {DOMAIN} as AVAILABLE.\n\n"
        f"RDAP cross-check: {rdap}\n\n"
        "Register it immediately if you want it. Availability can change at any time; "
        "this alert does not reserve the domain.\n"
        "Open Spaceship: https://www.spaceship.com/"
    )

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)

def mark_alert_sent():
    # Persist one-time alert state in a GitHub Actions repository variable.
    base = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/actions/variables/DOMAIN_ALERT_SENT"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    body = json.dumps({"name": "DOMAIN_ALERT_SENT", "value": "true"}).encode()
    status, payload = request_json(base, method="PATCH", headers=headers, body=body)
    if status == 404:
        status, payload = request_json(
            f"https://api.github.com/repos/{GITHUB_REPOSITORY}/actions/variables",
            method="POST", headers=headers, body=body
        )
    if status not in (201, 204):
        raise RuntimeError(f"Could not save alert state (HTTP {status}): {payload}")

def main():
    print(f"Checking {DOMAIN} with Spaceship...")
    available, payload = spaceship_availability()
    print(f"Spaceship result: {payload.get('result')}")

    if not available:
        print("Not available according to Spaceship. Will check again on next run.")
        return

    rdap = rdap_status()
    print(f"RDAP cross-check: {rdap}")

    if ALERT_SENT:
        print("Availability alert was already sent. No duplicate email.")
        return

    send_email(rdap)
    mark_alert_sent()
    print(f"Availability email sent to {os.environ['NOTIFY_EMAIL']}.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
