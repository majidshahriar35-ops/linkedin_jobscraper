# LinkedIn Jobs Daily Dashboard

Scrapes LinkedIn for **Entry Level AI / ML / Data Science** jobs posted in the last 24 hours,
then publishes an interactive HTML dashboard to GitHub Pages — automatically, every morning.

**Live URL after setup:** `https://<your-github-username>.github.io/<repo-name>/`

---

## Setup (one-time, ~5 minutes)

### 1 · Create a new GitHub repo

Go to [github.com/new](https://github.com/new) → name it anything (e.g. `linkedin-jobs`) →
set it to **Public** → click **Create repository**.

### 2 · Upload these files

Drop the following into the root of your repo (drag-and-drop on GitHub works fine):

```
generate_jobs.py
.github/
  workflows/
    daily_jobs.yml
README.md          ← optional
```

### 3 · Add your Apify API token as a secret

1. Get your token from [apify.com/account/integrations](https://console.apify.com/account/integrations)
2. In your repo → **Settings → Secrets and variables → Actions → New repository secret**
3. Name: `APIFY_TOKEN` · Value: paste your token → **Add secret**

### 4 · Enable GitHub Pages

In your repo → **Settings → Pages**:
- Source: **Deploy from a branch**
- Branch: `gh-pages` · Folder: `/ (root)`
- Click **Save**

> The `gh-pages` branch is created automatically on the first successful run.

### 5 · Trigger the first run manually

Go to **Actions → Daily LinkedIn Jobs Scrape → Run workflow → Run workflow**.

After ~3–5 minutes your dashboard will be live at:
```
https://<your-username>.github.io/<repo-name>/
```

---

## Customising

### Change the search queries

Edit `SEARCH_URLS` in `generate_jobs.py`:

```python
SEARCH_URLS = [
    "https://www.linkedin.com/jobs/search/?keywords=data%20scientist&f_E=2&f_TPR=r86400...",
    "https://www.linkedin.com/jobs/search/?keywords=machine%20learning%20engineer&f_E=2...",
    "https://www.linkedin.com/jobs/search/?keywords=AI%20engineer&f_E=2...",
]
```

**Seniority filters** (`f_E` param):

| Code | Level |
|------|-------|
| `f_E=1` | Internship |
| `f_E=2` | Entry level |
| `f_E=3` | Associate |
| `f_E=4` | Mid-Senior |

**Time window** (`f_TPR` param):

| Value | Window |
|-------|--------|
| `r86400` | Last 24 hours |
| `r604800` | Last 7 days |
| `r2592000` | Last 30 days |

### Change the schedule

Edit the cron line in `.github/workflows/daily_jobs.yml`:

```yaml
- cron: "0 12 * * *"   # noon UTC = 8 AM ET
```

Use [crontab.guru](https://crontab.guru) to build your expression.

---

## How it works

```
GitHub Actions (cron) → generate_jobs.py → Apify API
                                         ↓
                              curious_coder/linkedin-jobs-scraper
                                         ↓
                              Normalize + deduplicate jobs
                                         ↓
                              Write out/index.html
                                         ↓
                      peaceiris/actions-gh-pages → gh-pages branch
                                         ↓
                              GitHub Pages serves index.html
```

---

## Cost

- **GitHub Actions**: free on public repos (2,000 min/month on private)
- **Apify**: the actor costs roughly $0.001–$0.003 per run at 100 results — well within the free tier ($5/month credit)
