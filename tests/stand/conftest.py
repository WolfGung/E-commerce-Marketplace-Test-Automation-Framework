"""Fixtures for the stand's own contract tests: an app per test, no browser."""
from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import httpx
import pytest
import uvicorn

from stand.app.main import create_app

#: How long a fresh stand gets to start answering, and to stop.
START_TIMEOUT = 15.0
STOP_TIMEOUT = 15.0


@contextmanager
def served(app) -> Iterator[str]:
    """Serve `app` with uvicorn on a free loopback port and yield its base URL.

    The socket is bound here, before the server starts, so the port is known up
    front and nothing else can take it in between; uvicorn is handed the open
    socket rather than a port number.
    """
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True, name="stand")
    thread.start()
    deadline = time.monotonic() + START_TIMEOUT
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            server.should_exit = True
            listener.close()
            what = "exited before it was up" if not thread.is_alive() else f"did not start within {START_TIMEOUT:g} s"
            raise RuntimeError(f"the stand on port {port} {what}")
        time.sleep(0.05)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=STOP_TIMEOUT)
        listener.close()


@pytest.fixture
def app():
    """A fresh app per test: the account store and the sessions live on the app,
    so one test's account never leaks into the next. A test that checks the
    app's own state asks for this fixture next to `client`; both are the same app.
    """
    return create_app()


@pytest.fixture
def client(app) -> Iterator[httpx.Client]:
    # The app is served by uvicorn, as it is in the stand's image, so its
    # lifespan runs the way it runs there. The client keeps its own cookie jar,
    # which is what carries a session from one request to the next, and follows
    # redirects unless a test asks it not to: the tests that check a redirect
    # itself pass `follow_redirects=False`.
    with served(app) as base_url, httpx.Client(base_url=base_url, follow_redirects=True) as client:
        yield client


@pytest.fixture
def account_form() -> dict[str, str]:
    return {
        "name": "Ada Lovelace",
        "email": "ada.lovelace.4242@example.com",
        "password": "Qwerty!234",
        "title": "Mrs",
        "birth_date": "10",
        "birth_month": "12",
        "birth_year": "1985",
        "firstname": "Ada",
        "lastname": "Lovelace",
        "company": "Analytical Engines",
        "address1": "1 Difference Street",
        "address2": "Suite 2",
        "country": "United States",
        "zipcode": "10001",
        "state": "New York",
        "city": "New York",
        "mobile_number": "2125550123",
    }
