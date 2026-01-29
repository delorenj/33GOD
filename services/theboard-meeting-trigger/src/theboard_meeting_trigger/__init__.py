"""TheBoard meeting trigger consumer service - FastStream."""

from .consumer import app, broker

__version__ = "2.0.0"
__all__ = ["app", "broker"]
