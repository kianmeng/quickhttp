from contextlib import closing
from enum import Enum
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer, SimpleHTTPRequestHandler
from itertools import islice
import os
import random
import socket
from typing import Callable, Iterable, Tuple, Union

import typer

from quickhttp.exceptions import InvalidSearchTypeError, NoAvailablePortFoundError


def is_port_available(port: int) -> bool:
    """Check if port is available (not in use) on the local host. This is determined by attemping
    to create a socket connection with that port. If the connection is successful, that means
    something is using the port.

    Args:
        port (int): port to check.

    Returns:
        bool: If that port is available (not in use).
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            # Successfull connection
            return False
    return True


class SearchType(str, Enum):
    """Enum. Available types of search for
    [`find_available_port`][quickhttp.http_server.find_available_port].

    Attributes:
        sequential: Search ports sequentially in ascending order, starting with range_min.
        random: Search ports randomly within the interval [range_min, range_max].
    """

    sequential = "sequential"
    random = "random"


DEFAULT_PORT_RANGE_MIN: int = 8000
"""Default minimum of open port search range."""
DEFAULT_PORT_RANGE_MAX: int = 8999
"""Default maximum of open port search range."""
DEFAULT_PORT_MAX_TRIES: int = 50
"""Default maximum number of search attempts for an open port."""
DEFAULT_PORT_SEARCH_TYPE: SearchType = SearchType.sequential
"""Default type of search for [`find_available_port`][quickhttp.http_server.find_available_port].
See [`SearchType`][quickhttp.http_server.SearchType].
"""


def find_available_port(
    range_min: int = DEFAULT_PORT_RANGE_MIN,
    range_max: int = DEFAULT_PORT_RANGE_MAX,
    max_tries: int = DEFAULT_PORT_MAX_TRIES,
    search_type: SearchType = DEFAULT_PORT_SEARCH_TYPE,
) -> int:
    """Searches for an available port (not in use) on the local host.

    Args:
        range_min (int, optional): Minimum of range to search. Defaults to
            [DEFAULT_PORT_RANGE_MIN][quickhttp.http_server.DEFAULT_PORT_RANGE_MIN].
        range_max (int, optional): Maximum of range to search. Defaults to
            [DEFAULT_PORT_RANGE_MAX][quickhttp.http_server.DEFAULT_PORT_RANGE_MAX].
        max_tries (int, optional): Maximum number of ports to check. Defaults to
            [DEFAULT_PORT_MAX_TRIES][quickhttp.http_server.DEFAULT_PORT_MAX_TRIES].
        search_type (SearchType, optional): Type of search. See
            [SearchType][quickhttp.http_server.SearchType] enum for valid values. Defaults to
            [DEFAULT_PORT_SEARCH_TYPE][quickhttp.http_server.DEFAULT_PORT_SEARCH_TYPE].

    Raises:
        InvalidSearchTypeError: If search_type is invalid.
        NoAvailablePortFoundError: If no available ports found within max_tries.

    Returns:
        int: An available port.
    """
    max_tries = min(max_tries, range_max - range_min + 1)

    to_try: Iterable[int]
    if search_type == SearchType.sequential:
        to_try = islice(range(range_min, range_max + 1), max_tries)
    elif search_type == SearchType.random:
        to_try = random.sample(range(range_min, range_max + 1), max_tries)
    else:
        msg = (
            f"Invalid search_type {search_type}. Available options are "
            f"[{'|'.join(level.value for level in SearchType)}]."
        )
        raise InvalidSearchTypeError(msg)

    for port in to_try:
        if is_port_available(port=port):
            return port

    raise NoAvailablePortFoundError(
        f"Unable to find available port in range [{range_min}, {range_max}] with "
        f"{SearchType(search_type).value} search in {max_tries} tries."
    )


class TimedHTTPServer(HTTPServer):
    """Subclass of [`http.server.HTTPServer`](https://docs.python.org/3/library/http.server.html)
    that tracks timeout status.
    """

    def __init__(
        self,
        server_address: Tuple[str, int],
        RequestHandlerClass: Callable[..., BaseHTTPRequestHandler],
        timeout: int,
    ):
        self.timeout = timeout
        self.timeout_reached = False
        super().__init__(server_address=server_address, RequestHandlerClass=RequestHandlerClass)

    def handle_timeout(self):
        """Called if no new request arrives within self.timeout."""
        self.timeout_reached = True


def run_timed_http_server(
    address: str, port: int, directory: Union[str, os.PathLike], timeout: int
):
    """Start a [`TimedHTTPServer`][quickhttp.http_server.TimedHTTPServer] with specified timeout.

    Args:
        address (str): Address to bind the server to.
        port (int): Port to use.
        directory (Union[str, os.PathLike]): Directory to serve.
        timeout (int): Time to keep server alive for, in seconds.
    """
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))

    with TimedHTTPServer(
        server_address=(address, port), RequestHandlerClass=handler, timeout=timeout
    ) as httpd:
        try:
            while not httpd.timeout_reached:  # type: ignore
                httpd.handle_request()
            typer.echo("Timeout reached.")
        except KeyboardInterrupt:
            typer.echo(" KeyboardInterrupt received.")
