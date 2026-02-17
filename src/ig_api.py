"""Instagram API login — bypasses web form by using mobile API endpoints.

Uses Instagram's internal mobile API to authenticate, then injects the
session cookies into the browser. This avoids web-form automation detection.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# Instagram mobile API constants
IG_SIG_KEY = "9193488027538fd3450b83b7d05286d4ca9599a0f7eeed90d8c85571571eb57"
IG_APP_ID = "567067343352427"
API_URL = "https://i.instagram.com/api/v1"
USER_AGENT = "Instagram 275.0.0.27.98 Android (33/13; 420dpi; 1080x2400; samsung; SM-G991B; o1s; exynos2100; en_US; 458229258)"


def generate_device_id(username: str) -> str:
    """Generate a consistent device ID for a username."""
    seed = username.encode()
    m = hashlib.md5(seed)
    return f"android-{m.hexdigest()[:16]}"


def generate_uuid() -> str:
    return str(uuid.uuid4())


def sign_request(data: dict) -> str:
    """Sign a request payload for Instagram's API."""
    json_data = json.dumps(data, separators=(',', ':'))
    return urlencode({
        "signed_body": f"SIGNATURE.{json_data}",
        "ig_sig_key_version": "4",
    })


def instagram_api_login(username: str, password: str) -> dict[str, Any] | None:
    """Login to Instagram via mobile API.

    Returns:
        Dict with session cookies on success, None on failure.
    """
    device_id = generate_device_id(username)
    phone_id = generate_uuid()
    guid = generate_uuid()

    logger.info("Attempting Instagram API login for %s", username)

    # Step 1: Pre-login flow (get csrf token)
    headers = {
        "User-Agent": USER_AGENT,
        "X-IG-App-ID": IG_APP_ID,
        "X-IG-Device-ID": device_id,
        "X-IG-Android-ID": device_id,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    try:
        # Get CSRF token
        req = Request(f"{API_URL}/si/fetch_headers/?challenge_type=signup", headers=headers)
        req.add_header("X-DEVICE-ID", device_id)
        resp = urlopen(req, timeout=15)
        csrf_token = None
        for cookie in resp.headers.get_all("set-cookie") or []:
            if "csrftoken=" in cookie:
                csrf_token = cookie.split("csrftoken=")[1].split(";")[0]
                break

        if not csrf_token:
            logger.warning("Could not get CSRF token, continuing anyway")
            csrf_token = "missing"

    except Exception as e:
        logger.warning("Pre-login failed: %s, continuing anyway", e)
        csrf_token = "missing"

    # Step 2: Login request
    login_data = {
        "phone_id": phone_id,
        "_csrftoken": csrf_token,
        "username": username,
        "guid": guid,
        "device_id": device_id,
        "password": password,
        "login_attempt_count": "0",
    }

    body = sign_request(login_data).encode()

    login_headers = {
        **headers,
        "X-CSRFToken": csrf_token,
    }

    try:
        req = Request(f"{API_URL}/accounts/login/", data=body, headers=login_headers, method="POST")
        resp = urlopen(req, timeout=15)
        result = json.loads(resp.read())

        if result.get("status") == "ok" and result.get("logged_in_user"):
            user = result["logged_in_user"]
            logger.info("Instagram API login successful: %s (id: %s)", user.get("username"), user.get("pk"))

            # Extract session cookies from response
            cookies = []
            for header in resp.headers.get_all("set-cookie") or []:
                parts = header.split(";")
                if "=" in parts[0]:
                    name, value = parts[0].split("=", 1)
                    name = name.strip()
                    value = value.strip()
                    if name and value:
                        cookie = {
                            "name": name,
                            "value": value,
                            "domain": ".instagram.com",
                            "path": "/",
                            "secure": True,
                            "sameSite": "None",
                        }
                        # Parse expiry if present
                        for part in parts[1:]:
                            part = part.strip().lower()
                            if part.startswith("max-age="):
                                try:
                                    max_age = int(part.split("=")[1])
                                    cookie["expires"] = time.time() + max_age
                                except ValueError:
                                    pass
                        cookies.append(cookie)

            return {
                "success": True,
                "user": {
                    "id": user.get("pk"),
                    "username": user.get("username"),
                    "full_name": user.get("full_name", ""),
                },
                "cookies": cookies,
            }
        else:
            message = result.get("message", "Unknown error")
            logger.error("Instagram API login failed: %s", message)
            return {"success": False, "error": message}

    except Exception as e:
        error_msg = str(e)
        checkpoint_url = None
        # Try to parse error response
        if hasattr(e, "read"):
            try:
                err_body = json.loads(e.read())
                error_msg = err_body.get("message", error_msg)
                if error_msg == "checkpoint_required":
                    checkpoint_url = err_body.get("checkpoint_url", "")
                    logger.warning("Instagram checkpoint required: %s", checkpoint_url)
            except Exception:
                pass
        logger.error("Instagram API login error: %s", error_msg)
        result = {"success": False, "error": error_msg}
        if checkpoint_url:
            result["checkpoint_url"] = checkpoint_url
            result["needs_verification"] = True
        return result
