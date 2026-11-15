"""Sign-in for the Studio: email + one-time code, through Supabase Auth (no passwords, no JS SDK, no build step).

Flow:  POST /api/auth/send {email}          → Supabase emails a 6-digit code (creates the account on first sign-in)
       POST /api/auth/verify {email, code}  → Supabase returns a session; we keep it in two httpOnly cookies
       GET  /api/auth/me                    → the signed-in user (refreshes the session when the access token expired)
       POST /api/auth/logout                → ends the session, clears the cookies

Tokens never reach page JavaScript (httpOnly cookies, SameSite=Lax), so a script on the page cannot steal them.
Uses SUPABASE_URL plus SUPABASE_PUBLISHABLE_KEY (sb_publishable_..., preferred for Auth calls) or the existing
SUPABASE_SECRET_KEY. VAK_REQUIRE_LOGIN=1 makes creating, remixing, uploading and sharing films need a signed-in user.

Who sends the email:
  - RESEND_API_KEY set (preferred): the server asks Supabase for a code without sending anything (admin generate_link,
    needs SUPABASE_SECRET_KEY) and emails it with Resend from VAK_MAIL_FROM (default "Vāk <onboarding@resend.dev>",
    which Resend only delivers to the Resend account owner until a domain is verified). No Supabase email setup needed.
  - otherwise Supabase sends it: its "Magic link" and "Confirm signup" templates must contain {{ .Token }}, and real
    users need custom SMTP. See web/README.md → "Sign-in"."""
import json, os, re, threading, time, urllib.request, urllib.error
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

AT, RT = "vak_at", "vak_rt"                       # cookie names: access token (short), refresh token (long)
RT_AGE = 60 * 60 * 24 * 30                         # stay signed in for 30 days of inactivity at most
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
router = APIRouter(prefix="/api/auth")
_SENT, _SEEN, _LOCK = {}, {}, threading.Lock()     # email → last send time; access token → (user, checked at)


def cfg():
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "") or os.environ.get("SUPABASE_SECRET_KEY", "")
    return (url, key) if url and key.startswith(("sb_publishable_", "sb_secret_")) else (None, None)


def enabled():
    return cfg()[0] is not None


def required():
    return enabled() and os.environ.get("VAK_REQUIRE_LOGIN", "") in ("1", "true", "yes")


def _call(method, path, body=None, token=None, timeout=20, key=None):
    """(status, json) from Supabase Auth; network errors become a 503 for the browser."""
    url, k = cfg()
    key = key or k
    h = {"apikey": key, "content-type": "application/json"}
    if token:
        h["authorization"] = "Bearer " + token
    req = urllib.request.Request(url + "/auth/v1" + path, method=method, headers=h,
                                 data=json.dumps(body).encode("utf-8") if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}
    except OSError as e:
        raise HTTPException(503, f"Can't reach the sign-in service: {e}")


def _resend_on():
    return os.environ.get("RESEND_API_KEY", "").startswith("re_") and os.environ.get("SUPABASE_SECRET_KEY", "").startswith("sb_secret_")


def _mail_html(code):
    return f"""<div style="font-family:Inter,Segoe UI,Arial,sans-serif;max-width:440px;margin:0 auto;padding:28px 24px;color:#1b1722">
  <div style="width:44px;height:44px;border-radius:12px;background:#f2387a;background:linear-gradient(135deg,#ffb52e,#f2387a 55%,#7b5cff);color:#fff;font-size:20px;font-weight:600;text-align:center;line-height:44px">वा</div>
  <h2 style="font-size:20px;margin:18px 0 6px">Your Vāk sign-in code</h2>
  <p style="color:#5b5566;margin:0 0 18px">Enter this code in Vāk Studio. It expires in an hour.</p>
  <div style="font:700 30px/1 Consolas,Menlo,monospace;letter-spacing:8px;background:#f6f2ee;border-radius:12px;padding:18px;text-align:center">{code}</div>
  <p style="color:#8a8494;font-size:12.5px;margin-top:20px">If you didn't ask for this, you can ignore this email.<br>Vāk · understand what you chant</p></div>"""


def _send_with_resend(email):
    """Supabase makes the code (and the account on first sign-in) without emailing anything; Resend delivers it."""
    st, js = _call("POST", "/admin/generate_link", {"type": "magiclink", "email": email}, key=os.environ["SUPABASE_SECRET_KEY"])
    code = js.get("email_otp")
    if st >= 400 or not code:
        raise HTTPException(429 if st == 429 else 400, _msg(js, "Couldn't create a sign-in code"))
    body = {"from": os.environ.get("VAK_MAIL_FROM") or "Vāk <onboarding@resend.dev>", "to": [email],
            "subject": f"{code} is your Vāk sign-in code", "html": _mail_html(code),
            "text": f"Your Vāk sign-in code: {code}\nIt expires in an hour. If you didn't ask for it, ignore this email."}
    req = urllib.request.Request("https://api.resend.com/emails", method="POST",
                                 data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                 headers={"authorization": "Bearer " + os.environ["RESEND_API_KEY"],
                                          "content-type": "application/json", "user-agent": "vak-studio/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20):
            return
    except urllib.error.HTTPError as e:
        try:
            m = json.loads(e.read() or b"{}").get("message", "")
        except ValueError:
            m = ""
        print("resend:", e.code, m, flush=True)
        if e.code == 422:
            raise HTTPException(400, "That email address can't receive mail. Check it and try again")
        if e.code == 403:
            raise HTTPException(400, "Email is in test mode: it only reaches the Resend account owner until a domain is verified")
        raise HTTPException(502, "Couldn't send the email. Try again in a minute")
    except OSError as e:
        raise HTTPException(503, f"Can't reach the email service: {e}")


def _msg(js, fallback):
    return js.get("msg") or js.get("error_description") or js.get("message") or fallback


def _user(u):
    return {"id": u.get("id"), "email": u.get("email")}


def _secure():
    """Secure cookies (sent over HTTPS only) when hosted: Railway sets PORT and serves https in front of the app."""
    return bool(os.environ.get("PORT")) or os.environ.get("VAK_SECURE_COOKIES", "") in ("1", "true", "yes")


def _set(resp, s):
    sec = _secure()
    resp.set_cookie(AT, s["access_token"], max_age=int(s.get("expires_in", 3600)), httponly=True, secure=sec, samesite="lax", path="/")
    resp.set_cookie(RT, s["refresh_token"], max_age=RT_AGE, httponly=True, secure=sec, samesite="lax", path="/")


def _clear(resp):
    resp.delete_cookie(AT, path="/")
    resp.delete_cookie(RT, path="/")


def current_user(request: Request, response: Response | None = None):
    """The signed-in user {id, email} or None. Checks the token with Supabase (cached 60 s) and, given a response,
    swaps an expired access token for a new one using the refresh token."""
    if not enabled():
        return None
    at, rt = request.cookies.get(AT), request.cookies.get(RT)
    if at:
        with _LOCK:
            hit = _SEEN.get(at)
        if hit and time.time() - hit[1] < 60:
            return hit[0]
        st, js = _call("GET", "/user", token=at)
        if st == 200:
            u = _user(js)
            with _LOCK:
                if len(_SEEN) > 500:
                    _SEEN.clear()
                _SEEN[at] = (u, time.time())
            return u
    if rt and response is not None:
        st, js = _call("POST", "/token?grant_type=refresh_token", {"refresh_token": rt})
        if st == 200 and js.get("access_token"):
            _set(response, js)
            return _user(js.get("user") or {})
        _clear(response)
    return None


def need_user(request: Request, response: Response | None = None):
    """For endpoints that create things: the user when signed in; a 401 only when VAK_REQUIRE_LOGIN is on."""
    u = current_user(request, response)
    if u is None and required():
        raise HTTPException(401, "Sign in to create films")
    return u


class SendIn(BaseModel):
    email: str


class VerifyIn(BaseModel):
    email: str
    code: str


@router.get("/me")
def me(request: Request, response: Response):
    return {"enabled": enabled(), "required": required(), "user": current_user(request, response)}


@router.post("/send")
def send(body: SendIn):
    if not enabled():
        raise HTTPException(400, "Sign-in isn't set up: add SUPABASE_URL and a Supabase key to .env.local")
    email = body.email.strip().lower()
    if not EMAIL.match(email) or len(email) > 254:
        raise HTTPException(400, "That doesn't look like an email address")
    with _LOCK:                                          # Supabase also limits this; fail fast and say when to retry
        wait = 60 - (time.time() - _SENT.get(email, 0))
        if wait > 0:
            raise HTTPException(429, f"A code was just sent. Try again in {int(wait)} s")
        _SENT[email] = time.time()
    try:
        if _resend_on():
            _send_with_resend(email)
        else:
            st, js = _call("POST", "/otp", {"email": email, "create_user": True})
            if st >= 400:
                raise HTTPException(429 if st == 429 else 400, _msg(js, "Couldn't send the code"))
    except HTTPException:
        with _LOCK:
            _SENT.pop(email, None)
        raise
    return {"sent": True, "email": email}


@router.post("/verify")
def verify(body: VerifyIn, response: Response):
    if not enabled():
        raise HTTPException(400, "Sign-in isn't set up")
    email, code = body.email.strip().lower(), re.sub(r"\s", "", body.code)
    if not code.isdigit() or not 6 <= len(code) <= 10:
        raise HTTPException(400, "Enter the code from the email")
    st, js = _call("POST", "/verify", {"type": "email", "email": email, "token": code})
    if st >= 400 or not js.get("access_token"):
        raise HTTPException(400, "That code is wrong or has expired. Request a new one" if st < 500 else _msg(js, "Sign-in failed"))
    _set(response, js)
    return {"user": _user(js.get("user") or {})}


@router.post("/logout")
def logout(request: Request, response: Response):
    at = request.cookies.get(AT)
    if at and enabled():
        try:
            _call("POST", "/logout", token=at, timeout=8)    # revokes the refresh token on Supabase too
        except HTTPException:
            pass
        with _LOCK:
            _SEEN.pop(at, None)
    _clear(response)
    return {"ok": True}
