import pytest
import socket


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    original_connect = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0] if isinstance(address, tuple) and address else ""
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError(f"External network access blocked during tests: {host}")
        return original_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
