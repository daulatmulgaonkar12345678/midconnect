# Server Keep-Alive Configuration

## Overview

This document explains how to reduce backend cold-start delays on free hosting tiers (e.g., Render Free).

⚠️ Note: This setup minimizes cold starts but does NOT guarantee permanent uptime on free plans.

---

## Health Endpoint (Optimized)

### URL
https://midconnect.onrender.com/api/health

### Method
HEAD

### Expected Response
204 No Content

### Recommended Backend Implementation (FastAPI Example)

```python
from fastapi import Response

@app.head("/api/health")
@app.get("/api/health")
async def health():
    return Response(status_code=204)