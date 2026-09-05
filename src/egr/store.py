from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class StoredEnvelope:
    sequence: int
    payload_type: str
    payload: dict[str, Any]
    payload_sha256: str
    previous_envelope_sha256: str | None
    envelope_sha256: str


class IntegrityError(RuntimeError):
    pass


class HashChainRecordStore:
    """Append-only JSONL event store with a simple SHA-256 hash chain.

    This detects accidental or unsophisticated modification. It is not a
    substitute for signed records, trusted timestamps, or protected storage.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _raw_events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def verify(self) -> tuple[StoredEnvelope, ...]:
        events = self._raw_events()
        verified: list[StoredEnvelope] = []
        previous_digest: str | None = None
        for expected_sequence, envelope in enumerate(events, start=1):
            if envelope.get("sequence") != expected_sequence:
                raise IntegrityError(f"Sequence mismatch at event {expected_sequence}")
            if envelope.get("previous_envelope_sha256") != previous_digest:
                raise IntegrityError(f"Broken hash chain at event {expected_sequence}")
            if envelope.get("payload_sha256") != digest(envelope.get("payload")):
                raise IntegrityError(f"Payload digest mismatch at event {expected_sequence}")
            unsigned = {key: value for key, value in envelope.items() if key != "envelope_sha256"}
            envelope_digest = digest(unsigned)
            if envelope.get("envelope_sha256") != envelope_digest:
                raise IntegrityError(f"Envelope digest mismatch at event {expected_sequence}")
            previous_digest = envelope_digest
            verified.append(StoredEnvelope(**envelope))
        return tuple(verified)

    def append(self, payload_type: str, payload: dict[str, Any]) -> StoredEnvelope:
        events = self.verify()
        event_id = self._event_id(payload)
        if event_id and any(self._event_id(event.payload) == event_id for event in events):
            raise ValueError(f"Duplicate immutable event ID: {event_id}")
        unsigned = {
            "sequence": len(events) + 1,
            "payload_type": payload_type,
            "payload": payload,
            "payload_sha256": digest(payload),
            "previous_envelope_sha256": events[-1].envelope_sha256 if events else None,
        }
        envelope = {**unsigned, "envelope_sha256": digest(unsigned)}
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(envelope) + "\n")
        return StoredEnvelope(**envelope)

    @staticmethod
    def _event_id(payload: dict[str, Any]) -> str | None:
        for field in ("decision_id", "contract_id", "outcome_id"):
            if payload.get(field):
                return str(payload[field])
        return None

    def iter_payloads(self, payload_type: str | None = None) -> Iterator[dict[str, Any]]:
        for event in self.verify():
            if payload_type is None or event.payload_type == payload_type:
                yield event.payload
