# Chromium extension + GitHub Actions

This extension sends the current YouTube page URL to a localhost-only Python bridge. The bridge dispatches `.github/workflows/ytdlp-download.yml` in `unisocsu/yt-download`. It does not read or transmit browser cookies.

## Setup on Windows

1. Install Python 3.10 or newer.
2. Create a fine-grained GitHub token restricted to `unisocsu/yt-download`, with **Actions: Read and write**. Do not put the token in this repository or in the extension.
3. Open PowerShell in the `local-bridge` folder and set the token for that terminal session:
   `$env:GITHUB_TOKEN = "YOUR_TOKEN"`
4. Run `py -3 bridge.py`. Leave that window open. The server binds only to `127.0.0.1`.
5. In Chromium/Edge, open `chrome://extensions` (or `edge://extensions`), enable Developer mode, choose **Load unpacked**, and select the `browser-extension` folder.
6. Open a YouTube video, click the extension, and choose **Start download workflow**.
7. Open the repository's **Actions** tab. When the workflow completes, download the `ytdlp-download` artifact.

## Notes

- This initial version supports public YouTube URLs. It does not use Google login cookies.
- Keep the token only in your local environment; revoke it in GitHub settings if it is exposed.
- GitHub Actions artifacts expire after 3 days.
- Download only content you have permission to download and use.
