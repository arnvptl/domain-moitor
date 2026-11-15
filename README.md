# panipuri.cfd availability monitor

This project checks `panipuri.cfd` using Spaceship's availability API, cross-checks RDAP, and emails you once when Spaceship reports the domain as available.

**Scheduler:** cron-job.org triggers the GitHub Actions workflow using GitHub's `workflow_dispatch` API. cron-job.org does not execute the Python file itself.

## 1. Add GitHub repository secrets

In your repository, open **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | Value |
|---|---|
| `SPACESHIP_API_KEY` | Spaceship API key |
| `SPACESHIP_API_SECRET` | Spaceship API secret |
| `EMAIL_ADDRESS` | Gmail address used to send alerts |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not your normal Gmail password) |
| `NOTIFY_EMAIL` | Address that receives the alert |

Create a Spaceship API key with permission to read domain availability. Official docs: https://docs.spaceship.dev/

For Gmail, enable 2-Step Verification and create an App Password. Never commit credentials to the repository.

## 2. Create a fine-grained GitHub token for cron-job.org

In GitHub, open **Settings → Developer settings → Personal access tokens → Fine-grained tokens**.

- Repository access: select only this repository.
- Repository permissions: **Actions → Read and write**.
- Give it an expiry date.
- Generate and copy the token.

This token is used only by cron-job.org to start the workflow. Do not add it to this repository's files or commit it.

## 3. Create the cron-job.org job

Open https://console.cron-job.org/jobs and choose **Create cronjob**.

Configure:

| Field | Value |
|---|---|
| Title | `panipuri.cfd domain monitor` |
| URL | `https://api.github.com/repos/OWNER/REPO/actions/workflows/monitor.yml/dispatches` |
| Request method | `POST` |
| Schedule | Every 10 minutes |
| Request body | `{"ref":"main"}` |

Replace `OWNER/REPO` with your GitHub owner and repository name. Replace `main` if your default branch has another name.

Under advanced settings, add these headers:

| Header | Value |
|---|---|
| `Accept` | `application/vnd.github+json` |
| `Authorization` | `Bearer YOUR_FINE_GRAINED_GITHUB_TOKEN` |
| `X-GitHub-Api-Version` | `2022-11-28` |
| `Content-Type` | `application/json` |

Keep the GitHub token in the Authorization header field, not in the URL or request body.

Save the job, then use **Test Run**. A successful dispatch normally returns HTTP 204 with no response body. Open the repository's **Actions** tab and confirm that `Monitor panipuri.cfd` started.

## 4. How it behaves

- Spaceship `result: "taken"` means unavailable; the workflow exits normally and waits for the next cron trigger.
- Spaceship `result: "available"` triggers an RDAP diagnostic and one email notification.
- The workflow saves `DOMAIN_ALERT_SENT=true` as a repository Actions variable after successfully sending the email, preventing duplicate notifications.
- To re-arm alerts, delete or set the repository variable `DOMAIN_ALERT_SENT` to `false`.

## Important limitations

- cron-job.org schedules HTTP requests; GitHub Actions runs the Python program.
- The schedule is every 10 minutes. cron-job.org supports custom HTTP requests and scheduled execution, but delivery can be delayed.
- Spaceship availability is the deciding check. An RDAP 404 alone does not prove a registrar will accept a registration.
- The monitor does not reserve or automatically purchase the domain.
- If the workflow fails to save its alert state, check that the workflow has `variables: write` permission.
