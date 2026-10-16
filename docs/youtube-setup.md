# YouTube setup (one time, about 15 minutes)

Auto-posting to YouTube needs a small "app" in Google Cloud. It gives this repository permission to upload Shorts to **your new stickman channel**. Everything here is free.

You can reuse the Google Cloud project you already made for the infographic page (project 951613131027). It already has the YouTube API turned on, and the same app can post to many channels. Each channel just signs in once. If you'd rather keep the two separate, create a new project in step 1.

## 1. The Google Cloud project
1. Open [console.cloud.google.com](https://console.cloud.google.com) and pick the infographic project, or click **New project** (name it e.g. `stickman-reels`).
2. Go to **APIs & Services → Library**, search **YouTube Data API v3** and click **Enable**. If it says *Manage* instead, it's already on.

## 2. The consent screen (decides how long the sign-in lasts)
1. Go to **Google Auth Platform → Branding** ([console.cloud.google.com/auth/branding](https://console.cloud.google.com/auth/branding)).
   - **App name:** e.g. `Stickman Reels`.
   - Add your email as both the support and the developer contact.
2. **Audience** ([console.cloud.google.com/auth/audience](https://console.cloud.google.com/auth/audience)):
   - Set **User type** to **External**.
   - Then click **Publish app**, so the status says **In production**.

   This matters: while it says **Testing**, Google ends the sign-in after **7 days** and posting stops. In production, the sign-in keeps working.

   Google may show a "needs verification" notice. You don't need verification for your own channel: when signing in, click *Advanced → Go to Stickman Reels* (it is your own app).
3. **Data access:** add the scopes `.../auth/youtube.upload` and `.../auth/youtube.readonly`.

## 3. The client (what the sign-in uses)
1. Go to **Clients → Create client** ([console.cloud.google.com/auth/clients](https://console.cloud.google.com/auth/clients)).
   - **Application type:** **Desktop app**.
   - **Name:** `stickman-reels`.
2. Click **Download JSON**. This file is the client ID and secret, so keep it private and don't commit it.

   If you reuse the infographic project, you can reuse its existing Desktop client instead.

## 4. Sign in with the stickman channel (saves the 3 secrets)
On your PC, in the `stickman-reels` folder:

```bash
python tools/youtube_auth.py --save-to-github --client-file path/to/client_secret_XXXX.json
```

The browser opens. Sign in with the Google account that owns the **new stickman channel**. If that account has several channels (Brand Accounts), pick the stickman one when Google asks.

The script then saves `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` and `YOUTUBE_REFRESH_TOKEN` to this repository with the GitHub CLI. You never paste them anywhere.

## 5. Public uploads: the free API audit
Google keeps uploads from a new API project **private** until the project passes the free **YouTube API Services audit**. Fill in the [audit and quota form](https://support.google.com/youtube/contact/yt_api_form):
- **Use case:** "uploading my own channel's videos".
- It usually takes a few days to a few weeks.

Until then, posted Shorts arrive as private. The Telegram message tells you, and you can make them public in YouTube Studio. If the infographic project already passed the audit, reusing it avoids this wait.

## What then happens automatically
- **✅ Post** (or `AUTO_POST`) uploads each Short. With `POST_AT_PEAK`, it's scheduled for your best time.
- **Check YouTube sign-in** runs every morning at 07:30 IST:
  - If Google hands out a renewed refresh token, it's **saved back as the secret automatically**. This needs `GH_DISPATCH_TOKEN` with *Secrets: Read and write*.
  - If the sign-in will end (the app is still in Testing) or has stopped working (password change, access removed), you get a Telegram message with the one-command fix from step 4.
- A refresh token for an app in production doesn't expire on its own. Google only ends it when:
  - you remove the app's access;
  - you change the Google password (for some account types);
  - or it goes unused for 6 months. The daily check uses it, so that never happens.
