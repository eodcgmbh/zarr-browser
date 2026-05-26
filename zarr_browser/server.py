""" Application """

import dash
import dash_bootstrap_components as dbc
import flask


def _patch_zarr_v2_string_fill_value():
    """
    zarr v3 rejects fill_value=0 for string-dtype arrays from zarr v2 stores.
    Zarr v2 used 0 as the null fill value for fixed-length byte strings, which
    zarr v3's stricter parser refuses. Patch it to substitute "" instead.
    """
    try:
        from zarr.core.metadata.v2 import ArrayV2Metadata
        _orig = ArrayV2Metadata.from_dict.__func__

        @classmethod
        def _patched(cls, data):
            data = dict(data)
            dt = data.get("dtype", "")
            if isinstance(dt, str) and data.get("fill_value") == 0:
                if dt.startswith("|S") or dt.startswith("<U") or dt.startswith(">U"):
                    data["fill_value"] = ""
            return _orig(cls, data)

        ArrayV2Metadata.from_dict = _patched
    except Exception:
        pass


_patch_zarr_v2_string_fill_value()


server = flask.Flask(__name__)

app = dash.Dash(
    __name__,
    server=server,
    meta_tags=[
        {
            "name": "viewport",
            "content": "width=device-width, initial-scale=1, maximum-scale=1",
        }
    ],
    title="Zarr Browser",
    update_title=None,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.FLATLY],
)

app.index_string = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <link rel="icon" type="image/svg+xml" href="/assets/eodc-logo.svg">
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""
