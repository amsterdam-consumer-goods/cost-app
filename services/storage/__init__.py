"""Storage layer for catalog persistence."""

from .gist_storage import GistStorage, GistError

__all__ = ["GistStorage", "GistError"]