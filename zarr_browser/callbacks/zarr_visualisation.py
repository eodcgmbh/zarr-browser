""" callbacks to load and vis. Zarr metadata """

from dash.dependencies import Input, Output

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


def _viewer_button(store_id=None):
    base = get_viewer_url()
    if not base:
        return None
    href = f"{base.rstrip('/')}?dataset={store_id}" if store_id else base
    return html.A(
        [DashIconify(icon="mdi:map-outline", width=16), " Open in Map Viewer"],
        href=href,
        target="_blank",
        className="btn btn-sm",
        style={
            "backgroundColor": "var(--eodc-blue)",
            "color": "#fff",
            "borderRadius": "6px",
            "textDecoration": "none",
            "padding": "4px 12px",
        },
    )


def _metadata_card(dataset, chunks, shape, path_label="", store_id=None):
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

    viewer_btn = _viewer_button(store_id=store_id)
    return dbc.Card([
        dbc.CardHeader(html.Div([
            html.Div([
                html.H4([
                    DashIconify(icon="mdi:database-outline", width=20, color="#083A59"),
                    " Zarr Dataset",
                ], className="mb-1"),
                html.Div(path_label, style={"fontSize": "0.75rem", "color": "#737B8D", "fontFamily": "monospace"}),
            ], style={"flex": "1"}),
            *([viewer_btn] if viewer_btn else []),
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


# ── callback ──────────────────────────────────────────────────────────────────

@app.callback(Output("display-xarray", "children"), [Input("url", "pathname")])
def display_xarray_html(pathname):
    if pathname[-1] == "/":
        pathname = pathname[:-1]

    if not pathname.startswith("/zarr_store/"):
        return []

    parts = pathname[len("/zarr_store/"):].strip("/").split("/")
    store_id = parts[0]
    rest = parts[1:]

    store_cfg = get_store(store_id)
    if store_cfg is None:
        return [dbc.Alert(f"Store '{store_id}' not found in config.yaml.", color="danger")]

    tiles = store_cfg.get("tiles", [])
    resolutions = store_cfg.get("resolutions", [])

    if tiles:
        tile = rest[0] if rest else None
        if not tile:
            return [_no_dataset_card(store_cfg.get("name", ""))]
        if resolutions:
            resolution = rest[1] if len(rest) > 1 else None
            if not resolution:
                return [_no_dataset_card(store_cfg.get("name", ""))]
            store_url = resolve_store_url(store_cfg, tile=tile, resolution=resolution)
            subpath = "/".join(rest[2:])
        else:
            store_url = resolve_store_url(store_cfg, tile=tile)
            subpath = "/".join(rest[1:])
    else:
        store_url = resolve_store_url(store_cfg)
        subpath = "/".join(rest)

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
    return [_metadata_card(dataset, chunks, shape, path_label=label, store_id=store_id)]
