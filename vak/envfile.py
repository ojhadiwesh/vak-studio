"""Load local secrets (vak_engine/.env.local, written by `elevenlabs onboard`) into the environment with python-dotenv.
Values already set in the environment win. Nothing is printed or logged; the file stays out of git (.gitignore)."""
import os
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path=None):
    load_dotenv(path or os.path.join(ROOT, ".env.local"), override=False)
