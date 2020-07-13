from datetime import timedelta
from pathlib import Path
from typing import Optional

from pytimeparse import parse
import typer

from quickhttp.core import (
    __version__,
    DEFAULT_PORT_RANGE_MIN,
    DEFAULT_PORT_RANGE_MAX,
    DEFAULT_PORT_MAX_TRIES,
    DEFAULT_PORT_SEARCH_TYPE,
    find_available_port,
    run_timed_http_server,
    SearchType,
)

app = typer.Typer()


def version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def quickhttp(
    directory: Path = typer.Argument(
        ".", dir_okay=True, file_okay=False, readable=True, help="Directory to serve."
    ),
    time: str = typer.Option(
        "10m",
        "--time",
        "-t",
        help=(
            "Time to keep server alive for. Accepts time expressions parsable by pytimeparse, "
            "such as '10m' or '10:00'."
        ),
    ),
    port: Optional[int] = typer.Option(
        None,
        "--port",
        "-p",
        help=(
            "Port to use. If None (default), will automatically search for an open port using "
            "the other options. If specified, ignores other options."
        ),
    ),
    port_range_min: int = typer.Option(
        DEFAULT_PORT_RANGE_MIN, help="Minimum of range to search for an open port."
    ),
    port_range_max: int = typer.Option(
        DEFAULT_PORT_RANGE_MAX, help="Maximum of range to search for an open port."
    ),
    port_max_tries: int = typer.Option(
        DEFAULT_PORT_MAX_TRIES, help="Maximum number of ports to check."
    ),
    port_search_type: SearchType = typer.Option(
        DEFAULT_PORT_SEARCH_TYPE, help="Type of search to use."
    ),
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
        show_default=False,
    ),
):
    """Lightweight CLI that wraps Python's `http.server` with automatic port-finding and shutdown.
    """
    time_sec = parse(time)
    if not port:
        port = find_available_port(
            range_min=port_range_min,
            range_max=port_range_max,
            max_tries=port_max_tries,
            search_type=port_search_type,
        )
    typer.echo(
        f"Starting http.server at http://0.0.0.0:{port} for directory [{directory}]. "
        f"Server will stay alive for {str(timedelta(seconds=time_sec))}."
    )
    run_timed_http_server(port=port, directory=directory, time=time_sec)
    typer.echo("Server closed.")
