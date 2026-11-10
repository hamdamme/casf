"""Typed writer operations bound to an explicit log and existing Writer lifetime."""

from dataclasses import dataclass, field
from pathlib import Path

from casf.errors import SchemaError, TrustError
from casf.model.api import AppendResult, EventRequest, WitnessState
from casf.model.operations import Checkpoint, ExportResult, Manifest, WitnessResult
from casf.writer import Writer

__all__ = ['AppendResult', 'Checkpoint', 'EventRequest', 'ExportResult', 'LogHandle',
           'Manifest', 'WitnessResult', 'WitnessState', 'create_log', 'open_log']


@dataclass(frozen=True, slots=True, init=False)
class LogHandle:
    """Bind a log without owning the writer or granting startup authorization."""
    _writer: Writer = field(repr=False)
    manifest: Manifest

    def __init__(self, writer: Writer, log_id: str) -> None:
        manifest = Manifest(writer.manifest_envelope(log_id))
        if manifest.log_id != log_id:
            raise TrustError('stored manifest does not match the requested log')
        object.__setattr__(self, '_writer', writer)
        object.__setattr__(self, 'manifest', manifest)

    @property
    def log_id(self) -> str:
        return self.manifest.log_id

    def _bound_writer(self) -> Writer:
        if self._writer.manifest_envelope(self.log_id) != self.manifest.to_dict():
            raise TrustError('log handle no longer matches the stored manifest')
        return self._writer

    def append(self, request: EventRequest) -> AppendResult:
        return self._bound_writer().append_event(self.log_id, request)

    def create_checkpoint(self, *, final: bool = False) -> Checkpoint:
        return Checkpoint(self._bound_writer().create_checkpoint(self.log_id, final=final))

    def pending_checkpoint(self) -> Checkpoint | None:
        pending = self._bound_writer().pending_checkpoint(self.log_id)
        return Checkpoint(pending[0]) if pending is not None else None

    def submit_pending(self, base_url: str, token: str, *, timeout: float = 10.0) -> WitnessResult:
        receipt = self._bound_writer().submit_pending(self.log_id, base_url, token, timeout=timeout)
        return WitnessResult(receipt)

    def export_bundle(self, destination: str | Path, *, through: int | None = None) -> ExportResult:
        return self._bound_writer().export_bundle_result(self.log_id, destination, through=through)

    def seal_log(self) -> Checkpoint:
        return Checkpoint(self._bound_writer().seal_log(self.log_id))


def create_log(manifest: Manifest, writer: Writer) -> LogHandle:
    """Create through the configured writer; return a handle only after commit."""
    if not isinstance(manifest, Manifest):
        raise SchemaError('create_log requires a Manifest')
    writer.create_log(manifest.to_dict())
    return LogHandle(writer, manifest.log_id)


def open_log(writer: Writer, log_id: str) -> LogHandle:
    """Select a stored log without changing the writer's authorization policy."""
    return LogHandle(writer, log_id)
