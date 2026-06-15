from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def board_serve_command(
    board_dir: Path,
    port: int = 8765,
    dry_run: bool = False,
) -> dict[str, str | int]:
    board_dir = board_dir.resolve()
    if not board_dir.exists():
        msg = f"board directory does not exist: {board_dir}"
        raise FileNotFoundError(msg)
    if dry_run:
        return {"directory": str(board_dir), "port": port}
    handler = partial(SimpleHTTPRequestHandler, directory=str(board_dir))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"Serving Ariadne board at http://127.0.0.1:{server.server_port}/")
    server.serve_forever()
    return {"directory": str(board_dir), "port": server.server_port}
