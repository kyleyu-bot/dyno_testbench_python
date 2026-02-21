"""Cyclic EtherCAT process-data loop over configured slave adapters."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict

from .data_types import SystemCommand, SystemStatus
from .master import MasterRuntime


@dataclass(slots=True)
class LoopStats:
    """Basic loop timing and bus statistics."""

    cycle_count: int = 0
    last_wkc: int = 0
    last_cycle_time_ns: int = 0
    last_dc_error_ns: int = 0


class EthercatLoop:
    """Non-RT cyclic loop using master runtime and per-slave adapters."""

    def __init__(self, runtime: MasterRuntime, cycle_hz: int = 1000):
        if cycle_hz <= 0:
            raise ValueError("cycle_hz must be > 0")

        self._runtime = runtime
        self._cycle_hz = cycle_hz
        self._cycle_ns = int(1_000_000_000 / cycle_hz)

        self._lock = threading.Lock()
        self._pending_command = SystemCommand()
        self._latest_status = SystemStatus()
        self._stats = LoopStats()

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def stats(self) -> LoopStats:
        with self._lock:
            return LoopStats(
                cycle_count=self._stats.cycle_count,
                last_wkc=self._stats.last_wkc,
                last_cycle_time_ns=self._stats.last_cycle_time_ns,
                last_dc_error_ns=self._stats.last_dc_error_ns,
            )

    def set_command(self, command: SystemCommand) -> None:
        with self._lock:
            self._pending_command = command

    def get_status(self) -> SystemStatus:
        with self._lock:
            return SystemStatus(
                by_slave=dict(self._latest_status.by_slave),
                seq=self._latest_status.seq,
                stamp_ns=self._latest_status.stamp_ns,
            )

    def run_once(self) -> SystemStatus:
        start_ns = time.monotonic_ns()
        command = self._snapshot_command(start_ns)

        # Encode command payload for each configured slave adapter.
        for name, adapter in self._runtime.adapters.items():
            slave = self._runtime.slaves_by_name[name]
            payload = self._encode_payload(adapter, command.by_slave.get(name))
            slave.output = payload

        self._runtime.master.send_processdata()
        wkc = int(self._runtime.master.receive_processdata(2000))

        end_ns = time.monotonic_ns()
        cycle_time_ns = end_ns - start_ns
        dc_error_ns = cycle_time_ns - self._cycle_ns

        status_by_slave: Dict[str, Any] = {}
        for name, adapter in self._runtime.adapters.items():
            slave = self._runtime.slaves_by_name[name]
            status_by_slave[name] = adapter.unpack_tx_pdo(
                bytes(slave.input),
                seq=command.seq,
                stamp_ns=end_ns,
                cycle_time_ns=cycle_time_ns,
                dc_time_error_ns=dc_error_ns,
            )

        status = SystemStatus(by_slave=status_by_slave, seq=command.seq, stamp_ns=end_ns)
        with self._lock:
            self._latest_status = status
            self._stats.cycle_count += 1
            self._stats.last_wkc = wkc
            self._stats.last_cycle_time_ns = cycle_time_ns
            self._stats.last_dc_error_ns = dc_error_ns
        return status

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()

    def stop(self, timeout_s: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout_s)

    def _run_forever(self) -> None:
        next_tick = time.monotonic_ns()
        while not self._stop_event.is_set():
            self.run_once()
            next_tick += self._cycle_ns
            now = time.monotonic_ns()
            sleep_ns = next_tick - now
            if sleep_ns > 0:
                time.sleep(sleep_ns / 1_000_000_000)
            else:
                # Missed deadline, reset schedule to avoid accumulating drift.
                next_tick = now

    def _snapshot_command(self, stamp_ns: int) -> SystemCommand:
        with self._lock:
            seq = self._pending_command.seq + 1
            by_slave = dict(self._pending_command.by_slave)
            self._pending_command = SystemCommand(
                by_slave=by_slave, seq=seq, stamp_ns=stamp_ns
            )
            return self._pending_command

    @staticmethod
    def _encode_payload(adapter: Any, command: Any) -> bytes:
        if command is None:
            return bytes(adapter.rx_pdo_size)
        payload = adapter.pack_rx_pdo(command)
        if len(payload) != adapter.rx_pdo_size:
            raise ValueError(
                f"Encoded payload size mismatch: expected={adapter.rx_pdo_size} got={len(payload)}"
            )
        return payload
