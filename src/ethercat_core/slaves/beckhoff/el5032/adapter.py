"""Beckhoff EL5032 slave adapter placeholder."""

from __future__ import annotations

from dataclasses import dataclass

from ...base import SlaveIdentity
from .data_types import El5032Command, El5032Status


@dataclass(slots=True)
class El5032SlaveAdapter:
    """Placeholder adapter for Beckhoff EL5032 until PDO mapping is defined."""

    identity: SlaveIdentity

    @property
    def rx_pdo_size(self) -> int:
        raise NotImplementedError("EL5032 RX PDO mapping is not defined yet.")

    @property
    def tx_pdo_size(self) -> int:
        raise NotImplementedError("EL5032 TX PDO mapping is not defined yet.")

    def pack_rx_pdo(self, command: El5032Command) -> bytes:
        del command
        raise NotImplementedError("EL5032 RX PDO packing is not defined yet.")

    def unpack_tx_pdo(
        self,
        pdo: bytes,
        *,
        seq: int = 0,
        stamp_ns: int = 0,
        cycle_time_ns: int = 0,
        dc_time_error_ns: int = 0,
    ) -> El5032Status:
        del pdo, seq, stamp_ns, cycle_time_ns, dc_time_error_ns
        raise NotImplementedError("EL5032 TX PDO unpacking is not defined yet.")
