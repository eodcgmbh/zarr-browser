""" callbacks for remote zarr store navigation """

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from zarr_browser.server import app
from zarr_browser.store_config import load_stores, get_store, resolve_store_url
from dash import html, dcc
from dash_iconify import DashIconify
from functools import lru_cache
import json
import requests
import xarray


def _remote_icon():
    return DashIconify(icon="mdi:cloud-outline", color="#D9C991", width=15)

def _tile_icon():
    return DashIconify(icon="mdi:map-marker-outline", width=14, color="#A89154")

def _group_icon():
    return DashIconify(icon="mdi:folder-table-outline", width=14, color="#169EB0")


@lru_cache(maxsize=64)
def _load_subgroups(store_url):
    try:
        dt = xarray.open_datatree(store_url, engine="zarr")
        return tuple(sorted(dt.children.keys()))
    except Exception:
        pass
    try:
        resp = requests.get(store_url.rstrip("/") + "/.zmetadata", timeout=10)
        resp.raise_for_status()
        meta = json.loads(resp.text)
        groups = set()
        for key in meta.get("metadata", {}).keys():
            parts = key.strip("/").split("/")
            if len(parts) >= 2 and parts[-1] in (".zarray", ".zgroup"):
                groups.add(parts[0])
        return tuple(sorted(groups))
    except Exception:
        return ()


def _parse_path(pathname):
    """Return (store_id, parts) from a /zarr_store/... pathname."""
    if not pathname or not pathname.startswith("/zarr_store/"):
        return None, []
    parts = pathname[len("/zarr_store/"):].strip("/").split("/")
    return parts[0], parts[1:]


@app.callback(
    Output("subgroup-store", "data"),
    Input("url", "pathname"),
    State("subgroup-store", "data"),
)
def update_subgroup_store(pathname, current_data):
    store_id, rest = _parse_path(pathname)
    if not store_id:
        raise PreventUpdate

    store_cfg = get_store(store_id)
    if not store_cfg:
        raise PreventUpdate

    tiles = store_cfg.get("tiles", [])
    resolutions = store_cfg.get("resolutions", [])

    if tiles:
        tile = rest[0] if rest else None
        if not tile or tile not in tiles:
            cache_key = store_id
            if current_data and current_data.get("cache_key") == cache_key:
                raise PreventUpdate
            return {"cache_key": cache_key, "store_id": store_id, "tile": None,
                    "resolution": None, "subgroups": []}

        if resolutions:
            resolution = rest[1] if len(rest) > 1 else None
            if not resolution or resolution not in resolutions:
                cache_key = f"{store_id}/{tile}"
                if current_data and current_data.get("cache_key") == cache_key:
                    raise PreventUpdate
                return {"cache_key": cache_key, "store_id": store_id, "tile": tile,
                        "resolution": None, "subgroups": []}

            cache_key = f"{store_id}/{tile}/{resolution}"
            if current_data and current_data.get("cache_key") == cache_key:
                raise PreventUpdate

            tile_url = resolve_store_url(store_cfg, tile=tile, resolution=resolution)
            return {"cache_key": cache_key, "store_id": store_id, "tile": tile,
                    "resolution": resolution, "subgroups": list(_load_subgroups(tile_url))}
        else:
            cache_key = f"{store_id}/{tile}"
            if current_data and current_data.get("cache_key") == cache_key:
                raise PreventUpdate

            tile_url = resolve_store_url(store_cfg, tile=tile)
            return {"cache_key": cache_key, "store_id": store_id, "tile": tile,
                    "resolution": None, "subgroups": list(_load_subgroups(tile_url))}
    else:
        cache_key = store_id
        if current_data and current_data.get("cache_key") == cache_key:
            raise PreventUpdate

        store_url = resolve_store_url(store_cfg)
        return {"cache_key": cache_key, "store_id": store_id, "tile": None,
                "resolution": None, "subgroups": list(_load_subgroups(store_url))}


@app.callback(
    Output("file-system-display", "children"),
    Input("subgroup-store", "data"),
    State("url", "pathname"),
)
def display_file_system_page(subgroup_data, pathname):
    http_stores = load_stores()
    active_store_id, rest = _parse_path(pathname)

    items = []
    for s in http_stores:
        is_active = s["id"] == active_store_id
        tiles = s.get("tiles", [])

        items.append(html.Li(dcc.Link(
            [_remote_icon(), " " + s["name"]],
            href=f"/zarr_store/{s['id']}",
            className="sidebar-item remote active-store" if is_active else "sidebar-item remote",
        )))

        if not is_active:
            continue

        if tiles:
            resolutions = s.get("resolutions", [])
            active_tile = rest[0] if rest else None
            active_res = rest[1] if len(rest) > 1 and resolutions else None
            active_sg = rest[2] if len(rest) > 2 and resolutions else (rest[1] if len(rest) > 1 else None)

            for tile in tiles:
                is_active_tile = tile == active_tile
                items.append(html.Li(dcc.Link(
                    [_tile_icon(), " " + tile],
                    href=f"/zarr_store/{s['id']}/{tile}",
                    className="sidebar-subitem active-subitem" if is_active_tile else "sidebar-subitem",
                )))

                if not is_active_tile:
                    continue

                if resolutions:
                    for res in resolutions:
                        is_active_res = res == active_res
                        items.append(html.Li(dcc.Link(
                            [DashIconify(icon="mdi:magnify", width=14, color="#A89154"), f" {res}m"],
                            href=f"/zarr_store/{s['id']}/{tile}/{res}",
                            className="sidebar-subsubitem active-subitem" if is_active_res else "sidebar-subsubitem",
                        )))

                        if is_active_res and subgroup_data and subgroup_data.get("resolution") == res:
                            for sg in subgroup_data.get("subgroups", []):
                                cls = "sidebar-subsubsubitem active-subitem" if sg == active_sg else "sidebar-subsubsubitem"
                                items.append(html.Li(dcc.Link(
                                    [_group_icon(), " " + sg],
                                    href=f"/zarr_store/{s['id']}/{tile}/{res}/{sg}",
                                    className=cls,
                                )))
                else:
                    if subgroup_data and subgroup_data.get("tile") == tile:
                        for sg in subgroup_data.get("subgroups", []):
                            cls = "sidebar-subsubitem active-subitem" if sg == active_sg else "sidebar-subsubitem"
                            items.append(html.Li(dcc.Link(
                                [_group_icon(), " " + sg],
                                href=f"/zarr_store/{s['id']}/{tile}/{sg}",
                                className=cls,
                            )))
        else:
            active_sg = rest[0] if rest else None
            for sg in (subgroup_data or {}).get("subgroups", []):
                cls = "sidebar-subitem active-subitem" if sg == active_sg else "sidebar-subitem"
                items.append(html.Li(dcc.Link(
                    [_group_icon(), " " + sg],
                    href=f"/zarr_store/{s['id']}/{sg}",
                    className=cls,
                )))

    return html.Div([
        html.Div("Zarr Stores", className="sidebar-section-header"),
        html.Ul(items, style={"padding": 0, "margin": 0, "listStyle": "none"}),
    ])
