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
