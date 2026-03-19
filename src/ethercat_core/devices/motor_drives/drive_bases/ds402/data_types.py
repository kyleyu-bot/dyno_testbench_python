"""CiA 402 (DS402) command/status data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Tuple


class ModeOfOperation(IntEnum):
    """CiA 402 mode of operation (0x6060) values."""

    NO_MODE = 0
    PROFILE_POSITION = 1
    PROFILE_VELOCITY = 2
    PROFILE_TORQUE = 4
    CYCLIC_SYNC_POSITION = 8
    CYCLIC_SYNC_VELOCITY = 9
    CYCLIC_SYNC_TORQUE = 10


class DriveCiA402States(IntEnum):
    """
    CiA 402 drive-side state machine logical states.

    These are symbolic logical states, not raw statusword bitmasks.
    """

    NOT_READY_TO_SWITCH_ON = 0
    SWITCH_ON_DISABLED = 1
    READY_TO_SWITCH_ON = 2
    SWITCHED_ON = 3
    OPERATION_ENABLED = 4
    QUICK_STOP_ACTIVE = 5
    FAULT_REACTION_ACTIVE = 6
    FAULT = 7


@dataclass(slots=True)
class Command:
    """Command for one DS402 drive in engineering units."""

    mode_of_operation: ModeOfOperation = ModeOfOperation.NO_MODE
    target_torque_nm: float = 0.0
    target_velocity_rad_s: float = 0.0
    target_position_rad: float = 0.0
    torque_command_2022: float = 0.0
    torque_kp: float = 0.0
    torque_loop_max_output: float = 0.0
    torque_loop_min_output: float = 0.0
    velocity_loop_kp: float = 0.0
    velocity_loop_ki: float = 0.0
    velocity_loop_kd: float = 0.0
    position_loop_kp: float = 0.0
    position_loop_ki: float = 0.0
    position_loop_kd: float = 0.0
    enable_drive: bool = False
    clear_fault: bool = False
    seq: int = 0
    stamp_ns: int = 0


@dataclass(slots=True)
class DriveStatus:
    """Status for one DS402 drive in engineering units."""

    online: bool = False
    operational: bool = False
    faulted: bool = False
    al_state_code: int = 0
    cia402_state: DriveCiA402States = DriveCiA402States.NOT_READY_TO_SWITCH_ON
    status_word: int = 0
    mode_of_operation_display: int = 0
    error_code: int = 0
    ready_to_switch_on: bool = False
    switched_on: bool = False
    operation_enabled: bool = False
    fault: bool = False
    voltage_enabled: bool = False
    quick_stop_active: bool = False
    switch_on_disabled: bool = False
    warning: bool = False
    remote: bool = False
    target_reached: bool = False

    measured_torque_nm: float = 0.0
    measured_velocity_rad_s: float = 0.0
    measured_position_rad: float = 0.0
    velocity_command_received: float = 0.0
    bus_voltage: float = 0.0

    dc_time_error_ns: int = 0
    cycle_time_ns: int = 0

    slave_state_codes: Tuple[int, ...] = field(default_factory=tuple)
    seq: int = 0
    stamp_ns: int = 0
