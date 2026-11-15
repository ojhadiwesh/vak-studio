"""python -m web  [--port 8787] [--host 127.0.0.1]  -> the Vāk web app.
Hosted (Railway etc.): the platform sets PORT, so it listens on 0.0.0.0:$PORT, opens no browser and trusts the proxy's
X-Forwarded-* headers (https scheme for secure cookies)."""
import argparse, os, sys, webbrowser, threading
import uvicorn

hosted = bool(os.environ.get("PORT"))
ap = argparse.ArgumentParser(prog="web")
ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8787)))
ap.add_argument("--host", default="0.0.0.0" if hosted else "127.0.0.1")
ap.add_argument("--no-browser", action="store_true")
a = ap.parse_args()
os.environ.setdefault("PYTHONUTF8", "1")
if not a.no_browser and not hosted:
    threading.Timer(1.5, lambda: webbrowser.open(f"http://{a.host}:{a.port}")).start()
print(f"Vāk web app on http://{a.host}:{a.port}  (Ctrl+C to stop)", flush=True)
uvicorn.run("web.server:app", host=a.host, port=a.port, log_level="warning",
            proxy_headers=hosted, forwarded_allow_ips="*" if hosted else None)
