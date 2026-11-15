"""vak: Sanskrit chant -> illustrated, captioned film.
Modules: text, story, audio, visuals, motion, edit. All share one storyboard (see storyboard.py)."""
__version__ = "0.1.0"

from . import envfile as _envfile
_envfile.load()          # ELEVENLABS_API_KEY etc. from .env.local, for the engine CLI and the web app alike
