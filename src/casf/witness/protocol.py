"""Bound sockets and header waiting before the ASGI application is invoked.

The supported Uvicorn protocol class hook selects this h11 extension. Its
lifecycle overrides must be checked when the pinned Uvicorn version changes.
"""

import asyncio

from uvicorn.protocols.http.h11_impl import H11Protocol


def bounded_protocol(max_connections: int, header_timeout: float) -> type[H11Protocol]:
    class BoundedH11Protocol(H11Protocol):
        _header_deadline: asyncio.TimerHandle | None = None
        _rejected = False

        def connection_made(self, transport: asyncio.Transport) -> None:  # type: ignore[override]
            if len(self.connections) >= max_connections:
                self._rejected = True
                transport.close()
                return
            super().connection_made(transport)
            self._arm_header_deadline()

        def connection_lost(self, exc: Exception | None) -> None:
            self._cancel_header_deadline()
            if not self._rejected:
                super().connection_lost(exc)

        def data_received(self, data: bytes) -> None:
            if not self._rejected:
                super().data_received(data)

        def handle_events(self) -> None:
            previous = self.cycle
            super().handle_events()
            if self.cycle is not previous:
                self._cancel_header_deadline()

        def on_response_complete(self) -> None:
            super().on_response_complete()
            if not self.transport.is_closing() and self.cycle.response_complete:
                self._arm_header_deadline()

        def _arm_header_deadline(self) -> None:
            self._cancel_header_deadline()
            self._header_deadline = self.loop.call_later(header_timeout, self.transport.close)

        def _cancel_header_deadline(self) -> None:
            if self._header_deadline is not None:
                self._header_deadline.cancel()
                self._header_deadline = None

    return BoundedH11Protocol
