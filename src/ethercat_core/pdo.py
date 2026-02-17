"""PDO packing and unpacking helpers for EtherCAT cyclic exchange."""

from __future__ import annotations

from dataclasses import dataclass
from struct import Struct

from .data_types import (
    Command,
    DriveCiA402States,
    DriveStatus,
    EthercatAlStates,
)

# Master -> drive cyclic command payload (example/baseline layout).
_RX_PDO_STRUCT = Struct("<Hbhii")

# Drive -> master cyclic status payload (example/baseline layout).
_TX_PDO_STRUCT = Struct("<HbHhiiB")


@dataclass(slots=True)
class PdoScaling:
    """
    Conversion factors between engineering units and raw PDO integer units.

    These defaults are placeholders and should be tuned per drive/PDO map.
    """

    torque_lsb_per_nm: float = 10.0
    velocity_lsb_per_rad_s: float = 1000.0
    position_lsb_per_rad: float = 10000.0


def _clamp_i16(value: int) -> int:
    return max(-32768, min(32767, value))


def _clamp_i32(value: int) -> int:
    return max(-2147483648, min(2147483647, value))


def decode_cia402_state(status_word: int) -> DriveCiA402States:
    """
    Decode CiA 402 logical state from statusword (0x6041).

    Masks follow common CiA 402 state decoding patterns.
    """

    state_004f = status_word & 0x004F
    state_006f = status_word & 0x006F

    if state_004f == 0x0000:
        return DriveCiA402States.NOT_READY_TO_SWITCH_ON
    if state_004f == 0x0040:
        return DriveCiA402States.SWITCH_ON_DISABLED
    if state_004f == 0x0021:
        return DriveCiA402States.READY_TO_SWITCH_ON
    if state_004f == 0x0023:
        return DriveCiA402States.SWITCHED_ON
    if state_004f == 0x0027:
        return DriveCiA402States.OPERATION_ENABLED
    if state_006f == 0x0007:
        return DriveCiA402States.QUICK_STOP_ACTIVE
    if state_004f == 0x000F:
        return DriveCiA402States.FAULT_REACTION_ACTIVE
    if state_004f == 0x0008:
        return DriveCiA402States.FAULT

    # Fallback keeps behavior safe if a vendor adds uncommon combinations.
    return DriveCiA402States.NOT_READY_TO_SWITCH_ON


def _controlword_from_command(command: Command) -> int:
    if command.clear_fault:
        return 0x0080
    if command.enable_drive:
        return 0x000F
    return 0x0006


def pack_command(command: Command, scaling: PdoScaling | None = None) -> bytes:
    """Pack application `Command` into the configured RX PDO byte layout."""

    cfg = scaling or PdoScaling()
    controlword = _controlword_from_command(command)
    mode = int(command.mode_of_operation)
    target_torque = _clamp_i16(round(command.target_torque_nm * cfg.torque_lsb_per_nm))
    target_velocity = _clamp_i32(
        round(command.target_velocity_rad_s * cfg.velocity_lsb_per_rad_s)
    )
    target_position = _clamp_i32(
        round(command.target_position_rad * cfg.position_lsb_per_rad)
    )

    return _RX_PDO_STRUCT.pack(
        controlword, mode, target_torque, target_velocity, target_position
    )


def unpack_status(
    pdo: bytes,
    scaling: PdoScaling | None = None,
    *,
    seq: int = 0,
    stamp_ns: int = 0,
    cycle_time_ns: int = 0,
    dc_time_error_ns: int = 0,
) -> DriveStatus:
    """Unpack TX PDO bytes into `DriveStatus`."""

    if len(pdo) < _TX_PDO_STRUCT.size:
        raise ValueError(
            f"TX PDO payload too small: got={len(pdo)} expected={_TX_PDO_STRUCT.size}"
        )

    cfg = scaling or PdoScaling()
    (
        status_word,
        mode_display,
        error_code,
        measured_torque_raw,
        measured_velocity_raw,
        measured_position_raw,
        al_state_code,
    ) = _TX_PDO_STRUCT.unpack_from(pdo, 0)

    cia402_state = decode_cia402_state(status_word)
    al_state_base = al_state_code & 0x0F

    return DriveStatus(
        online=al_state_base != 0,
        operational=al_state_base == int(EthercatAlStates.OPERATIONAL),
        faulted=(cia402_state in (DriveCiA402States.FAULT, DriveCiA402States.FAULT_REACTION_ACTIVE)),
        al_state_code=al_state_code,
        cia402_state=cia402_state,
        status_word=status_word,
        mode_of_operation_display=mode_display,
        error_code=error_code,
        measured_torque_nm=measured_torque_raw / cfg.torque_lsb_per_nm,
        measured_velocity_rad_s=measured_velocity_raw / cfg.velocity_lsb_per_rad_s,
        measured_position_rad=measured_position_raw / cfg.position_lsb_per_rad,
        dc_time_error_ns=dc_time_error_ns,
        cycle_time_ns=cycle_time_ns,
        seq=seq,
        stamp_ns=stamp_ns,
    )
