# Server Keep-Alive Configuration

## Overview
This document provides instructions for setting up external monitoring to prevent backend cold starts on free hosting tiers.

## Health Endpoint

**URL:** `https://your-backend-url.com/api/health`  
**Method:** GET  
**Expected Response:**
```json
{
  "status": "ok",
  "service": "midconnect-api",
  "timestamp": "2026-02-27T05:00:00.000Z",
  "uptime": "active"
}
```

---

## Option 1: UptimeRobot (Recommended - Free)

1. Go to [UptimeRobot](https://uptimerobot.com/)
2. Create free account
3. Click "Add New Monitor"
4. Configure:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** MidConnect API
   - **URL:** `https://your-backend-url.com/api/health`
   - **Monitoring Interval:** 5 minutes
5. Enable email alerts for downtime
6. Save

---

## Option 2: Cron-job.org (Free)

1. Go to [Cron-job.org](https://cron-job.org/)
2. Create free account
3. Click "Create cronjob"
4. Configure:
   - **Title:** MidConnect Keep Alive
   - **URL:** `https://your-backend-url.com/api/health`
   - **Schedule:** Every 5 minutes (`*/5 * * * *`)
   - **Request Method:** GET
5. Enable notifications
6. Save

---

## Option 3: GitHub Actions (Included)

A GitHub Actions workflow is already configured at `.github/workflows/keep-alive.yml`.

### Setup:
1. Push to GitHub
2. Go to Settings > Secrets > Actions
3. Add secret: `BACKEND_URL` = your production backend URL
4. The workflow runs automatically every 5 minutes

---

## Frontend Warm-Up (Automatic)

The frontend includes a `ServerWarmUp` component that:
- Pings `/api/health` when users visit the site
- Shows "Connecting to secure marketplace server..." if response takes >1.5s
- Stores session flag to avoid repeated warm-ups
- Runs silently in background

---

## Recommended Setup

For **best results**, use **both**:
1. ✅ External ping (UptimeRobot) - keeps server warm 24/7
2. ✅ Frontend warm-up - ensures instant response for user's first action

This combination provides:
- Zero cold-start delays
- 99.9% uptime monitoring
- Email alerts for downtime
- Professional user experience
