""" base layout """

import dash_bootstrap_components as dbc
from dash import dcc, html


def base_layout() -> html.Div:
    return html.Div([
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="subgroup-store", storage_type="memory"),

        # ── Code modal ────────────────────────────────────────
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle([
                html.Span("Load with xarray", style={"fontFamily": "MarkOT, sans-serif"}),
            ])),
            dbc.ModalBody([
                html.Div([
                    dcc.Clipboard(target_id="code-block-pre", className="zb-copy-btn"),
                    html.Pre(id="code-block-pre", className="zb-code-block"),
                ], style={"position": "relative"}),
            ]),
        ], id="code-modal", size="lg", is_open=False),

        # ── Navbar ────────────────────────────────────────────
        html.Nav(
            dbc.Container([
                dcc.Link(
                    [
                        html.Img(
                            src="/assets/eodc-logo.svg",
                            height=28,
                            style={"filter": "brightness(0) invert(1)"},
                        ),
                        html.Span("Zarr Browser", className="zb-brand ms-2"),
                    ],
                    href="/",
                    className="zb-brand text-decoration-none",
                ),
            ], fluid=True),
            className="zb-navbar d-flex align-items-center",
        ),

        # ── Body ──────────────────────────────────────────────
        html.Div([
            dbc.Row([
                dbc.Col(
                    html.Div([
                        html.Div(id="file-system-display"),
                        html.Div(
                            html.Img(src="/assets/eodc-logo.svg", style={"width": "75%"}),
                            className="zb-sidebar-logo",
                        ),
                    ], className="zb-sidebar-inner"),
                    id="sidebar",
                    width=3,
                    className="px-0",
                ),
                dbc.Col(
                    html.Div(id="display-xarray"),
                    id="content",
                    width=9,
                ),
            ], className="g-0 h-100"),
        ]),
    ])
