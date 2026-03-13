#!/usr/bin/env python3
"""Read Beckhoff EL3002 registers through SDO and optionally sample live PDO data."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Allow direct execution before install.
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ethercat_core.loop import EthercatLoop
from ethercat_core.master import (
    EthercatMaster,
    MasterConfigError,
    load_topology,
    require_pysoem,
    resolve_slave_position,
)
from ethercat_core.slaves.beckhoff.el3002.adapter import El3002SlaveAdapter
from ethercat_core.slaves.beckhoff.el3002.data_types import EL3002_TX_PDO_FIELDS, El3002Data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Poll a Beckhoff EL3002 register through SDO and optionally print a live PDO field."
    )
    parser.add_argument(
        "--topology",
        default="config/topology.dyno2.template3.json",
        help="Path to topology JSON file.",
    )
    parser.add_argument(
        "--slave",
        default="analog_input_interface",
        help="Configured EL3002 slave name to observe.",
    )
    parser.add_argument(
        "--index",
        type=lambda x: int(x, 0),
        default=0x8000,
        help="SDO object index to read, for example 0x3101.",
    )
    parser.add_argument(
        "--subindex",
        type=lambda x: int(x, 0),
        default=0x03,
        help="SDO object subindex to read, for example 0x01.",
    )
    parser.add_argument(
        "--duration-s",
        type=float,
        default=60.0,
        help="Monitor duration in seconds.",
    )
    parser.add_argument(
        "--print-hz",
        type=float,
        default=5.0,
        help="Register print rate.",
    )
    parser.add_argument(
        "--pdo-index",
        type=lambda x: int(x, 0),
        default=0x1A01,
        help="Optional mapped TxPDO field index to print from live process data, for example 0x1A01.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    require_pysoem()

    cfg = load_topology(args.topology)
    resolved_position = resolve_slave_position(cfg, args.slave)
    for slave_cfg in cfg.slaves:
        if slave_cfg.name == args.slave:
            slave_cfg.position = resolved_position
            break

    pdo_field = next(
        (field for field in EL3002_TX_PDO_FIELDS if field.pdo_index == args.pdo_index),
        None,
    )
    if pdo_field is None:
        available = ", ".join(f"0x{field.pdo_index:04X}" for field in EL3002_TX_PDO_FIELDS)
        raise ValueError(
            f"Unsupported EL3002 PDO field 0x{args.pdo_index:04X}. Available: {available}"
        )

    master = EthercatMaster(cfg)
    loop: EthercatLoop | None = None
    try:
        runtime = master.initialize()
        adapter = runtime.adapters.get(args.slave)
        if not isinstance(adapter, El3002SlaveAdapter):
            raise RuntimeError(
                f"Slave '{args.slave}' is not an EL3002. Adapter={type(adapter).__name__}"
            )

        slave = runtime.slaves_by_name[args.slave]
        loop = EthercatLoop(runtime, cycle_hz=cfg.cycle_hz)
        loop.start()

        deadline = time.monotonic() + max(0.0, args.duration_s)
        print_period = 1.0 / max(args.print_hz, 0.1)
        next_print = time.monotonic()

        print(
            f"Monitoring '{args.slave}' at position {resolved_position} "
            f"register 0x{args.index:04X}:{args.subindex:02X} through SDO "
            f"and live PDO 0x{args.pdo_index:04X} "
            f"for {args.duration_s:.1f}s"
        )

        while time.monotonic() < deadline:
            now = time.monotonic()
            if now >= next_print:
                raw = slave.sdo_read(args.index, args.subindex)
                if isinstance(raw, int):
                    value = int(raw)
                    width = max(1, (value.bit_length() + 8) // 8)
                    payload_hex = value.to_bytes(width, "little", signed=value < 0).hex()
                elif isinstance(raw, (bytes, bytearray)):
                    payload = bytes(raw)
                    payload_hex = payload.hex()
                    value = int.from_bytes(payload, "little", signed=True)
                else:
                    raise TypeError(f"Unexpected SDO payload type: {type(raw)}")

                status = loop.get_status().by_slave.get(args.slave)
                pdo_raw_hex = "unavailable"
                pdo_value = "unavailable"
                if isinstance(status, El3002Data):
                    field_end = pdo_field.offset + pdo_field.size
                    if len(status.raw_pdo) >= field_end:
                        pdo_slice = status.raw_pdo[pdo_field.offset:field_end]
                        pdo_raw_hex = pdo_slice.hex()
                        pdo_value = str(
                            int.from_bytes(
                                pdo_slice,
                                byteorder="little",
                                signed=pdo_field.signed,
                            )
                        )

                print(
                    f"raw_sdo={payload_hex} "
                    f"register_0x{args.index:04X}_{args.subindex:02X}={value} "
                    f"pdo_0x{args.pdo_index:04X}_raw={pdo_raw_hex} "
                    f"pdo_0x{args.pdo_index:04X}={pdo_value}"
                )
                next_print = now + print_period
            time.sleep(0.005)

        return 0
    finally:
        if loop is not None:
            loop.stop()
        master.close()


if __name__ == "__main__":
    raise SystemExit(main())
