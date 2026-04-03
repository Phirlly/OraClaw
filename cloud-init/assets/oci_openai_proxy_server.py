#!/usr/bin/env python3
"""Thin entrypoint for OCI OpenAI proxy.

This file is intentionally NOT named `oci_openai_proxy.py` to avoid a Python
import-name collision with the `oci_openai_proxy` package.

Cloud-init installs:
- this file to /usr/local/bin/oci_openai_proxy_server.py
- the package to /usr/local/lib/oci_openai_proxy

Systemd runs this entrypoint.
"""

from oci_openai_proxy.app import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    from oci_openai_proxy import config

    uvicorn.run(app, host=config.PROXY_HOST, port=config.PROXY_PORT)
