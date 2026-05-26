""" plotly dash app """

import os
from zarr_browser.templates.base import base_layout
from zarr_browser.server import app, server

from zarr_browser.callbacks.file_system import display_file_system_page  # noqa:F401
from zarr_browser.callbacks.zarr_visualisation import display_xarray_html  # noqa:F401

app.layout = base_layout()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    server.run(
        host="0.0.0.0",
        port=port,
        threaded=False,
        processes=4,
    )
