"""Vercel entry point: exposes the FastAPI app as a Python serverless function."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from twinorch.api.app import create_app  # noqa: E402

app = create_app()
