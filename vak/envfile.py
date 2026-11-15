"""Load local secrets (vak_engine/.env.local, written by `elevenlabs onboard`) into the environment with python-dotenv.
Values already set in the environment win. Nothing is printed or logged; the file stays out of git (.gitignore)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path=None):
    try:
        from dotenv import load_dotenv
    except ImportError:          # the offline eval/red-team scripts need no secrets, so python-dotenv is optional
        return
    load_dotenv(path or os.path.join(ROOT, ".env.local"), override=False)
