"""Load zarr store configs from config.yaml."""

import os
import yaml
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("STORE_CONFIG", "/app/config.yaml"))


def load_stores():
    if not CONFIG_PATH.exists():
        return []
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f) or {}
    return cfg.get("zarr_stores", [])


def get_store(store_id):
    return next((s for s in load_stores() if s["id"] == store_id), None)


def resolve_store_url(store_cfg, tile=None, resolution=None):
    """Return the actual zarr URL, resolving {tile} and {resolution} template placeholders."""
    if "url_template" in store_cfg:
        if tile is None:
            return None
        tmpl = store_cfg["url_template"]
        kwargs = {"tile": tile}
        if "{resolution}" in tmpl:
            kwargs["resolution"] = resolution or ""
        return tmpl.format(**kwargs)
    return store_cfg.get("url")


def get_stac_url():
    if not CONFIG_PATH.exists():
        return None
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f) or {}
    return cfg.get("stac_url")


def get_viewer_url():
    if not CONFIG_PATH.exists():
        return None
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f) or {}
    return cfg.get("viewer_url")
