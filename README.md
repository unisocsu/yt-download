# Chromium DOM Downloader

GitHub Actions workflow that opens Chromium with Playwright, optionally injects a JavaScript init script, clicks a DOM element, saves a browser download under `downloads/`, verifies it, and uploads it as an artifact.

## Run it

1. Open **Actions** → **Chromium DOM download** → **Run workflow**.
2. Enter the URL.
3. For a page that has a download button, set `download_selector` to its CSS selector.
4. If the page needs an initial button click to open a dialog, set `prepare_selector`.
5. Optionally set `script_url` to an HTTPS URL for JavaScript you trust. The script is injected before page scripts.
6. Click **Run workflow**. When successful, open the run and download the `downloaded-file` artifact.

### Direct-file mode

For a direct file URL that triggers a normal browser download, leave `download_selector` and `prepare_selector` blank.

### DOM-click mode

- `url`: webpage containing the controls.
- `prepare_selector` (optional): CSS selector clicked first, such as a button that opens a download dialog.
- `download_selector` (required for DOM mode): CSS selector clicked to trigger the actual browser download.
- `script_url` (optional): HTTPS URL of JavaScript to inject before the page's scripts.
- `timeout_seconds`: timeout clamped to 30–900 seconds.

The final click must trigger a **real browser download**. A page that fetches data into an internal JavaScript buffer, uses a custom download manager, or opens a new window without a browser download event may need a site-specific adapter; this generic runner will report a timeout rather than claim success.

## Security and permissions

Only use URLs and scripts you trust, and only download files you are authorized to access. A supplied `script_url` runs as JavaScript in every page loaded by the browser context, so it can access that page's content. Do not pass secrets in the URL or script. Artifacts are retained for 3 days.
