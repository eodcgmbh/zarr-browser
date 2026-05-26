""" callbacks to load and vis. Zarr metadata """

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from zarr_browser.server import app
from zarr_browser.store_config import get_store, get_viewer_url, resolve_store_url
from dash import html
import xarray
from dask.array.svg import svg
from dask.array.core import normalize_chunks
from dask.utils import format_bytes
import numpy as np
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_store_from_path(pathname):
    """Returns (store_cfg, store_url, subpath) or None if not a valid zarr path."""
    if pathname.endswith("/"):
        pathname = pathname[:-1]
    if not pathname.startswith("/zarr_store/"):
        return None

    parts = pathname[len("/zarr_store/"):].strip("/").split("/")
    store_id = parts[0]
    rest = parts[1:]

    store_cfg = get_store(store_id)
    if store_cfg is None:
        return None

    tiles = store_cfg.get("tiles", [])
    resolutions = store_cfg.get("resolutions", [])

    if tiles:
        tile = rest[0] if rest else None
        if not tile:
            return store_cfg, None, None
        if resolutions:
            resolution = rest[1] if len(rest) > 1 else None
            if not resolution:
                return store_cfg, None, None
            store_url = resolve_store_url(store_cfg, tile=tile, resolution=resolution)
            subpath = "/".join(rest[2:])
        else:
            store_url = resolve_store_url(store_cfg, tile=tile)
            subpath = "/".join(rest[1:])
    else:
        store_url = resolve_store_url(store_cfg)
        subpath = "/".join(rest)

    return store_cfg, store_url, subpath


def _no_dataset_card(store_name=""):
    return dbc.Card(dbc.CardBody([
        html.Div([
            DashIconify(icon="mdi:folder-table-outline", width=32, color="#169EB0"),
            html.H5(store_name or "Select a subgroup", className="mt-2 mb-1",
                    style={"color": "var(--eodc-dark-blue)"}),
            html.P("Choose a subgroup from the sidebar to explore its dataset.",
                   className="text-muted mb-0", style={"fontSize": "0.875rem"}),
        ], style={"textAlign": "center", "padding": "2rem 0"}),
    ]), className="zb-card")


def _get_chunks_shape(dataset):
    var_name = list(dataset.data_vars)[0]
    var = dataset[var_name]
    shape = tuple(var.shape)
    chunks = var.encoding.get("chunks")
    if chunks is None and hasattr(var.data, "chunks"):
        chunks = tuple(c[0] for c in var.data.chunks)
    if chunks is None:
        chunks = shape
    return tuple(chunks), shape


def _btn_style(bg="var(--eodc-blue)"):
    return {"backgroundColor": bg, "color": "#fff", "borderRadius": "6px",
            "textDecoration": "none", "padding": "4px 12px", "border": "none", "cursor": "pointer"}


def _viewer_button(store_id=None):
    base = get_viewer_url()
    if not base:
        return None
    href = f"{base.rstrip('/')}?dataset={store_id}" if store_id else base
    return html.A(
        [DashIconify(icon="mdi:map-outline", width=16), " Map Viewer"],
        href=href, target="_blank", className="btn btn-sm", style=_btn_style(),
    )


def _stac_button(store_cfg):
    url = store_cfg.get("stac-url")
    if not url:
        return None
    return html.A(
        [DashIconify(icon="mdi:layers-search-outline", width=16), " STAC"],
        href=url, target="_blank", className="btn btn-sm",
        style=_btn_style("var(--eodc-dark-grey)"),
    )


def _code_button():
    return html.Button(
        [DashIconify(icon="mdi:code-braces", width=16), " Python"],
        id="code-btn", n_clicks=0, className="btn btn-sm", style=_btn_style("var(--eodc-gold)"),
    )


def _make_code_snippet(store_url, subpath=""):
    lines = [
        "import xarray as xr",
        "",
        "ds = xr.open_dataset(",
        f'    "{store_url}",',
        '    engine="zarr",',
    ]
    if subpath:
        lines.append(f'    group="{subpath}",')
    lines.append(")")
    return "\n".join(lines)


def _metadata_card(dataset, chunks, shape, path_label="", store_cfg=None):
    store_id = store_cfg.get("id") if store_cfg else None
    total_chunks = int(np.prod([np.ceil(s / c).astype(int) for s, c in zip(shape, chunks)]))

    var_pills = [html.Span(v, className="zb-pill") for v in dataset.data_vars]

    stat_table = dbc.Table([
        html.Thead(html.Tr([html.Th(""), html.Th("Array"), html.Th("Chunk")])),
        html.Tbody([
            html.Tr([
                html.Th("Bytes"),
                html.Td(format_bytes(dataset.nbytes)),
                html.Td(format_bytes(dataset.nbytes / total_chunks) if total_chunks else "—"),
            ]),
            html.Tr([html.Th("Shape"), html.Td(str(shape)), html.Td(str(chunks))]),
            html.Tr([html.Th("Chunks"), html.Td(f"{total_chunks:,} total"), html.Td("")]),
        ]),
    ], size="sm", className="zb-stat-table mb-0", bordered=False)

    btns = [b for b in [_viewer_button(store_id=store_id), _stac_button(store_cfg or {}), _code_button()] if b]
    return dbc.Card([
        dbc.CardHeader(html.Div([
            html.Div([
                html.H4([
                    DashIconify(icon="mdi:database-outline", width=20, color="#083A59"),
                    " Zarr Dataset",
                ], className="mb-1"),
                html.Div(path_label, style={"fontSize": "0.75rem", "color": "#737B8D", "fontFamily": "monospace"}),
            ], style={"flex": "1"}),
            html.Div(btns, style={"display": "flex", "gap": "0.5rem"}),
        ], style={"display": "flex", "alignItems": "center", "gap": "1rem"})),
        dbc.CardBody([
            html.Div(var_pills, className="mb-3"),
            dbc.Row([
                dbc.Col(stat_table, md=6),
                dbc.Col(html.Iframe(
                    srcDoc=svg(normalize_chunks(chunks, shape), size=200),
                    style={"border": "none", "height": "200px", "width": "100%"},
                ), md=6),
            ], className="mb-3"),
        ]),
        html.Iframe(
            srcDoc=dataset._repr_html_(),
            style={"border": "none", "width": "100%", "height": "35vh"},
            className="zb-xarray-frame",
        ),
    ], className="zb-card")


# ── callbacks ─────────────────────────────────────────────────────────────────

@app.callback(
    Output("display-xarray", "children"),
    Input("url", "pathname"),
)
def display_xarray_html(pathname):
    result = _parse_store_from_path(pathname)
    if result is None:
        return []

    store_cfg, store_url, subpath = result
    if store_url is None:
        return [_no_dataset_card(store_cfg.get("name", ""))]

    open_kwargs = {"engine": "zarr"}
    if subpath:
        open_kwargs["group"] = subpath

    try:
        dataset = xarray.open_dataset(store_url, **open_kwargs)
    except Exception:
        try:
            dataset = xarray.open_dataset(store_url, consolidated=False, **open_kwargs)
        except Exception:
            return [_no_dataset_card(store_cfg.get("name", ""))]

    if not dataset.data_vars:
        return [_no_dataset_card(store_cfg.get("name", ""))]

    chunks, shape = _get_chunks_shape(dataset)
    label = store_url + ("/" + subpath if subpath else "")
    return [_metadata_card(dataset, chunks, shape, path_label=label, store_cfg=store_cfg)]


@app.callback(
    Output("code-modal", "is_open"),
    Output("code-block-pre", "children"),
    Input("code-btn", "n_clicks"),
    State("url", "pathname"),
    State("code-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_code_modal(n_clicks, pathname, is_open):
    if not n_clicks:
        raise PreventUpdate
    code = ""
    result = _parse_store_from_path(pathname)
    if result is not None:
        store_cfg, store_url, subpath = result
        if store_url is not None:
            code = _make_code_snippet(store_url, subpath or "")
    return not is_open, code
