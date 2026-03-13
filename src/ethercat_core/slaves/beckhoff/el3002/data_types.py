"""Beckhoff EL3002 command/data model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class El3002PdoField:
    """One EL3002 TX PDO field mapping."""

    name: str
    pdo_index: int
    offset: int
    size: int
    signed: bool = False


# Mapping order based on SDO-observed TxPDO entry sizes:
# 0x1A00 AnalogInput(ch1), 0x1A01 Samples(ch1), 0x1A10 Timestamp,
# 0x1A21 AnalogInput(ch2), 0x1A22 Samples(ch2).
#
# Only the byte spans are considered authoritative here. The internal
# subfield meaning for each 4-byte / 8-byte object is intentionally deferred
# until the slave object dictionary is fully decoded.
EL3002_INPUT_FIELD_SIZE = 4
EL3002_SAMPLES_FIELD_SIZE = 4
EL3002_TIMESTAMP_FIELD_SIZE = 8
EL3002_TX_PDO_FIELDS = (
    El3002PdoField("input_1", 0x1A00, 0, EL3002_INPUT_FIELD_SIZE),
    El3002PdoField(
        "samples_1",
        0x1A01,
        EL3002_INPUT_FIELD_SIZE,
        EL3002_SAMPLES_FIELD_SIZE,
    ),
    El3002PdoField(
        "timestamp",
        0x1A10,
        EL3002_INPUT_FIELD_SIZE + EL3002_SAMPLES_FIELD_SIZE,
        EL3002_TIMESTAMP_FIELD_SIZE,
    ),
    El3002PdoField(
        "input_2",
        0x1A21,
        EL3002_INPUT_FIELD_SIZE
        + EL3002_SAMPLES_FIELD_SIZE
        + EL3002_TIMESTAMP_FIELD_SIZE,
        EL3002_INPUT_FIELD_SIZE,
    ),
    El3002PdoField(
        "samples_2",
        0x1A22,
        EL3002_INPUT_FIELD_SIZE
        + EL3002_SAMPLES_FIELD_SIZE
        + EL3002_TIMESTAMP_FIELD_SIZE
        + EL3002_INPUT_FIELD_SIZE,
        EL3002_SAMPLES_FIELD_SIZE,
    ),
)
EL3002_TX_PDO_SIZE = sum(field.size for field in EL3002_TX_PDO_FIELDS)


@dataclass(slots=True)
class El3002Command:
    """Command model for an input-only EL3002 terminal."""


@dataclass(slots=True)
class El3002Data:
    """Observed EL3002 process-data state."""

    input_1: int = 0
    samples_1: int = 0
    timestamp: int = 0
    input_2: int = 0
    samples_2: int = 0
    raw_pdo: bytes = field(default_factory=bytes)
