# panipuri.cfd availability monitor

A GitHub Actions workflow that checks `panipuri.cfd` against Spaceship's domain-availability API every 10 minutes and sends one email when Spaceship reports it as available.

It also queries the authoritative RDAP service discovered through IANA's RDAP bootstrap registry. RDAP is diagnostic only: an RDAP 404 does **not** guarantee that a registrar will allow registration.

## 1. Create a Spaceship API key

In your Spaceship account, open API Manager and create an API key/secret with permission to read domain availability (`domains:read`).

Official API docs: https://docs.spaceship.dev/

## 2. Configure GitHub repository secrets

Create a GitHub repository and add these under **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `SPACESHIP_API_KEY` | Spaceship API key |
| `SPACESHIP_API_SECRET` | Spaceship API secret |
| `EMAIL_ADDRESS` | Gmail address used to send alerts |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not your normal Gmail password) |
| `NOTIFY_EMAIL` | Address that should receive the alert |

For Gmail, enable 2-Step Verification and create an App Password. If your Google account does not offer App Passwords, use another SMTP provider and adapt `send_email()`.

## 3. Push these files to the default branch

Keep the paths exactly as shown:

```text
.github/
  workflows/
    monitor.yml
monitor.py
```

Enable GitHub Actions for the repository. The workflow runs on a schedule and can also be started manually from the Actions tab.

## 4. Reset after an alert

The workflow creates the repository Actions variable `DOMAIN_ALERT_SENT=true` after the first successful email. This prevents repeated alerts.

To monitor again, go to **Settings → Secrets and variables → Actions → Variables**, edit `DOMAIN_ALERT_SENT` to `false`, or delete it. The next successful run will resume alerting.

## Notes and limitations

- The schedule is every 10 minutes, not real-time. GitHub may delay scheduled runs during high load.
- Spaceship availability is the decisive check for this workflow. The domain may become unavailable again between a notification and your registration attempt.
- This workflow does not automatically purchase the domain.
- The Spaceship API may require an eligible account/API access and can change. If the API returns 401/403, check API key permissions and account access. If it returns 429, increase the interval.
- Do not commit API keys, Gmail app passwords, or other credentials into the repository.
