---
name: glados-automatic-checkin
description: Complete blueprint for GLaDOS & Railgun multi-account check-in automation. Includes production Python scripts, cron wrappers, PushDeer integration, and strict troubleshooting guides.
version: 1.1.0
author: 程序员Devil & Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [checkin, automation, glados, pushdeer, cron, python]
    related_skills: [automatic-sign-in-maintenance, hermes-agent-skill-authoring]
---

# GLaDOS & Railgun Automatic Check-in Blueprint

This skill contains the production-grade automation setup, deployment workflows, and systematic troubleshooting routines for GLaDOS / Railgun automatic daily check-in and points exchange. It includes full codebases for Python sign-in scripts, wrapper scripts, scheduler deployment guides, and strict troubleshooting steps designed for multi-account publishing.

## Overview
The automated check-in blueprint leverages GLaDOS APIs to automatically:
1. **Check remaining package days** (`/api/user/status`).
2. **Perform daily sign-ins** (`/api/user/checkin`) with multi-domain failover (`glados.cloud`, `glados.rocks`, `railgun.info`).
3. **Query total points balance** (`/api/user/points`).
4. **Exchange accumulated points for active packages** (`/api/user/exchange` e.g., plan500).
5. **Deliver real-time mobile push notifications** via PushDeer.

---

## When to Use
- **Use when**: Setting up, maintaining, scaling, or migrating daily check-in automation for GLaDOS/Railgun.
- **Do NOT use for**: Services that enforce rigid client-side interactive CAPTCHAs (like Cloudflare Turnstile or reCAPTCHA Enterprise) unless combined with browser automation/solver bypass.

---

## 1. Core Source Code Blueprint

### A. Core Script (`checkin.py`)
```python
import requests
import json
import os
import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from pypushdeer import PushDeer
from logging_config import init_logger

class CheckinStatus(Enum):
    SUCCESS = 0
    REPEAT = 1
    FAILURE = -2

class ExchangePlan(Enum):
    PLAN100 = "plan100"
    PLAN200 = "plan200"
    PLAN500 = "plan500"

class APIEndpoint(Enum):
    CHECKIN = "/api/user/checkin"
    STATUS = "/api/user/status"
    POINTS = "/api/user/points"
    EXCHANGE = "/api/user/exchange"

class LogEmoji:
    SUCCESS = "✅"
    FAIL = "❌"
    REPEAT = "🔄"
    CHECKIN = "🎫"
    STATUS = "📊"
    POINTS = "💰"
    EXCHANGE = "🎁"
    START = "🚀"
    END = "🏁"
    COOKIE = "🍪"
    DOMAIN = "🌐"
    WARNING = "⚠️"
    ERROR = "🔴"
    INFO = "ℹ️"

def log_method(func):
    def wrapper(self, *args, **kwargs):
        method_name = func.__name__
        emoji_map = {
            "checkin": LogEmoji.CHECKIN,
            "get_status": LogEmoji.STATUS,
            "get_points": LogEmoji.POINTS,
            "exchange": LogEmoji.EXCHANGE,
        }
        emoji = emoji_map.get(method_name, LogEmoji.INFO)
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logger.error(f"{LogEmoji.COOKIE}[{self.cookie_index}] {LogEmoji.DOMAIN}[{self.domain}] {LogEmoji.ERROR} {method_name} failed: {e}")
            DEFAULT_ERRORS = {
                "checkin": {"status": "Check-in Failed", "points": "0", "message": str(e)},
                "get_status": ("None Days", -2),
                "get_points": ("None Points", 0),
                "exchange": f"Failed: {e}",
            }
            return DEFAULT_ERRORS.get(method_name)
    return wrapper

class Config:
    ENV_PUSH_KEY = "PUSHDEER_SENDKEY"
    ENV_COOKIES = "GLADOS_COOKIES"
    ENV_EXCHANGE_PLAN = "GLADOS_EXCHANGE_PLAN"
    ENV_VERBOSE = "GLADOS_VERBOSE"
    DEFAULT_EXCHANGE_PLAN = "plan500"
    DEFAULT_VERBOSE = False
    DOMAINS = ["glados.cloud", "railgun.info"]
    EXCHANGE_PLANS = {"plan100": 100, "plan200": 200, "plan500": 500}

    def __init__(self):
        self.push_key = os.environ.get(self.ENV_PUSH_KEY, "")
        raw_cookies = os.environ.get(self.ENV_COOKIES, "")
        self.cookies_list = [c.strip() for c in raw_cookies.split("&") if c.strip()]
        self.exchange_plan = os.environ.get(self.ENV_EXCHANGE_PLAN, self.DEFAULT_EXCHANGE_PLAN)
        verbose_str = os.environ.get(self.ENV_VERBOSE, "false").lower()
        self.verbose = verbose_str in ["true", "1", "yes", "y"]

class API:
    def __init__(self, domain: str, cookie_index: int = 0, verbose: bool = False):
        self.domain = domain
        self.cookie_index = cookie_index
        self.verbose = verbose
        self.headers = {
            "origin": f"https://{self.domain}",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def close(self):
        if hasattr(self, "session"):
            self.session.close()

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.close(); return False

    def _make_request(self, path: str, method: str, data: Optional[Dict] = None, cookies: str = "") -> Optional[requests.Response]:
        url = f"https://{self.domain}{path}"
        headers = self.headers.copy()
        headers["cookie"] = cookies
        try:
            if method.upper() == "POST":
                # Crucial Fix: Use json=data to ensure application/json Content-Type is auto-applied!
                return self.session.post(url, headers=headers, json=data, timeout=(30, 60))
            return self.session.get(url, headers=headers, timeout=(30, 60))
        except Exception as e:
            logger.error(f"Network error to {url}: {e}")
            return None

    @log_method
    def checkin(self, cookies: str) -> Dict:
        response = self._make_request(APIEndpoint.CHECKIN.value, "POST", {"token": self.domain}, cookies)
        result = {"status": "Check-in Failed", "points": "0", "message": "Network error", "code": CheckinStatus.FAILURE}
        if response:
            data = response.json()
            code = data.get("code", -2)
            msg = data.get("message", "No message")
            points = str(data.get("points", 0))
            if code == CheckinStatus.SUCCESS.value:
                result.update({"status": "Check-in Success", "points": points, "message": msg, "code": CheckinStatus.SUCCESS})
            elif code == CheckinStatus.REPEAT.value:
                result.update({"status": "Already Checked In", "points": "0", "message": msg, "code": CheckinStatus.REPEAT})
            else:
                result.update({"message": msg})
        return result

    @log_method
    def get_status(self, cookies: str) -> Tuple[str, int]:
        response = self._make_request(APIEndpoint.STATUS.value, "GET", cookies=cookies)
        if response:
            data = response.json()
            days = data.get("data", {}).get("leftDays")
            if days is not None:
                return f"{int(float(days))} Days", data.get("code", 0)
        return "None Days", -2

    @log_method
    def get_points(self, cookies: str) -> Tuple[str, int]:
        response = self._make_request(APIEndpoint.POINTS.value, "GET", cookies=cookies)
        if response:
            data = response.json()
            pts = data.get("points")
            if pts is not None:
                return f"{int(float(pts))} Points", int(float(pts))
        return "None Points", 0

    @log_method
    def exchange(self, cookies: str, plan: str, req_points: int) -> str:
        response = self._make_request(APIEndpoint.EXCHANGE.value, "POST", {"planType": plan}, cookies)
        if response:
            data = response.json()
            if data.get("code") == 0:
                return f"Exchanged: {plan}"
            return f"Exchange Failed: {data.get('message', 'Unknown Error')}"
        return "Exchange Failed"

@dataclass
class CheckinResult:
    cookie_index: int
    domain: str
    status: str = "Check-in Failed"
    points: str = "0"
    days: str = "None"
    points_total: str = "None"
    exchange: str = "No Exchange"
    code: CheckinStatus = CheckinStatus.FAILURE

class Checker:
    def __init__(self, config: Config):
        self.config = config
        self.results: List[CheckinResult] = []

    def checkin_all(self):
        for idx, cookie in enumerate(self.config.cookies_list, 1):
            for domain in self.config.DOMAINS:
                res = self._checkin_on_domain(cookie, idx, domain)
                self.results.append(res)

    def _checkin_on_domain(self, cookie: str, idx: int, domain: str) -> CheckinResult:
        res = CheckinResult(idx, domain)
        with API(domain, idx, self.config.verbose) as api:
            days_str, status_code = api.get_status(cookie)
            res.days = days_str
            if status_code != -2:
                checkin_res = api.checkin(cookie)
                res.status = checkin_res["status"]
                res.code = checkin_res["code"]
                res.points = checkin_res["points"]
                
                pts_str, pts_num = api.get_points(cookie)
                res.points_total = pts_str
                
                req_pts = self.config.EXCHANGE_PLANS.get(self.config.exchange_plan, 500)
                if pts_num >= req_pts:
                    res.exchange = api.exchange(cookie, self.config.exchange_plan, req_pts)
        return res

    def format_results(self) -> Tuple[str, str, str]:
        success = sum(1 for r in self.results if r.code == CheckinStatus.SUCCESS)
        repeat = sum(1 for r in self.results if r.code == CheckinStatus.REPEAT)
        fail = sum(1 for r in self.results if r.code == CheckinStatus.FAILURE)
        title = f"GLaDOS Check-in: Success {success}, Repeat {repeat}, Failed {fail}"
        details = "\n".join([f"#{r.cookie_index} [{r.domain}] {r.status} | Remaining: {r.days} | Points: {r.points_total} | {r.exchange}" for r in self.results])
        return title, details, details

def main():
    config = Config()
    if not config.cookies_list:
        logger.error("No valid cookies found!")
        return
    checker = Checker(config)
    checker.checkin_all()
    title, details, _ = checker.format_results()
    print(f"[{title}]\n{details}")
    if config.push_key:
        PushDeer(pushkey=config.push_key).send_text(title, desp=details)

if __name__ == "__main__":
    main()
```

### B. Structured Logging Configuration (`logging_config.py`)
```python
import logging.config
import datetime

def beijing_time_converter(timestamp):
    utc_dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
    beijing_dt = utc_dt.astimezone(beijing_tz)
    return beijing_dt.timetuple()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "converter": beijing_time_converter,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

def init_logger():
    logging.config.dictConfig(LOGGING_CONFIG)
    return logging.getLogger()
```

---

## 2. Scheduler & Run Wrapper Blueprint

To execute securely inside environment isolation (like crontab, systemd, or Hermes scheduling), wrap the python run inside a bash daemon.

### Production Wrapper (`checkin.sh`)
```bash
#!/bin/bash
# Multi-account automatic check-in scheduler wrapper with retry logic
export GLADOS_COOKIES="koa:sess=YOUR_COOKIE_A; koa:sess.sig=YOUR_SIG_A&koa:sess=YOUR_COOKIE_B; koa:sess.sig=YOUR_SIG_B"
export PUSHDEER_SENDKEY="PDBOX1234567890..."
export GLADOS_EXCHANGE_PLAN="plan500"

# Navigate to execution context
cd "$(dirname "$0")"
source venv/bin/activate

MAX_RETRIES=3
RETRY_COUNT=0
SUCCESS=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Attempting check-in (Try $((RETRY_COUNT + 1))/$MAX_RETRIES)..."
    OUTPUT=$(python3 checkin.py 2>&1)
    echo "$OUTPUT"
    
    if echo "$OUTPUT" | grep -qE "Check-in Success|Already Checked In|重复签到|签到成功"; then
        SUCCESS=true
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo "Check-in unconfirmed. Retrying in 30 seconds..."
        sleep 30
    fi
done

if [ "$SUCCESS" = false ]; then
    echo "ERROR: Automatic check-in failed after $MAX_RETRIES attempts."
    exit 1
fi
exit 0
```

---

## 3. High-Priority Pitfalls (Critical)

1. **The Ellipsis Truncation Trap (`...`)**
   - **Symptom**: Requests return `{"code": -2, "message": "No permission"}` or `{"code": -2, "message": "没有权限"}`.
   - **Cause**: Copying the cookie string from chat client (like WeChat) or browser tools often truncates long strings with `...` (e.g. `koa:sess=eyJ...123`).
   - **Fix**: Verify cookies in terminal using `grep -q "\.\.\."` before running. Ensure they are fully expanded.

2. **JSON POST Content-Type Failure**
   - **Symptom**: Point exchange fails with error: `{"code": 1, "message": "Plan type is required"}`.
   - **Cause**: In Python's `requests` library, passing `data=json.dumps(payload)` to `requests.post()` without explicitly mapping the header `"Content-Type": "application/json"` causes the remote parser to ignore the body.
   - **Fix**: Use the explicit `json=data` parameter in `requests.post()` which automatically manages headers, or explicitly inject `"Content-Type": "application/json"`.

3. **Multi-Domain Failover Strategy**
   - Accounts are unified across GLaDOS subdomains. Do not fail the whole cron execution if a secondary domain (e.g. `railgun.info` or `glados.cloud`) fails, as long as **at least one** primary endpoint reports `SUCCESS` or `Already Checked In`.

4. **WeChat Login QR Verification and Margins (Quiet Zone)**
   - **Problem**: When rendering browser-derived base64 QR codes to WeChat scanners, scanning fails silently.
   - **Cause**: Mobile camera scanners rely on a solid white margin of 4 modules (~80px wide) called the *Quiet Zone* to lock onto contrast markers.
   - **Fix**: Always pad base64-decoded images using Python PIL before rendering:
     ```python
     from PIL import Image, ImageOps
     img = Image.open(BytesIO(base64.b64decode(b64_img)))
     padded = ImageOps.expand(img, border=80, fill="white")
     padded.save("padded_qr.png", "PNG")
     ```

---

## 4. Verification Checklist

- [ ] Run `python3 checkin.py` manually with dummy cookies to confirm config fails gracefully.
- [ ] Inject raw complete cookies into `GLADOS_COOKIES` and confirm response code is `0` or `1`.
- [ ] If using PushDeer, verify mobile push notification contains accurate balances (Points total, Remaining days).
- [ ] Set up crontab scheduler `0 8 * * * /path/to/checkin.sh` and ensure exit code `0` is captured under successful runs.
