"""Beckhoff EL3002 slave adapter implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...base import SlaveIdentity
from .data_types import (
    EL3002_TX_PDO_FIELDS,
    EL3002_TX_PDO_SIZE,
    El3002Command,
    El3002Data,
)

EL3002_ALLOWED_TORQUE_SCALES = (20.0, 200.0, 500.0)


@dataclass(slots=True)
class El3002SlaveAdapter:
    """Adapter for Beckhoff EL3002 2-channel analog input terminal."""

    identity: SlaveIdentity
    samples_1_torque_scale: float = 200.0
    samples_2_torque_scale: float = 20.0

    def __post_init__(self) -> None:
        self.samples_1_torque_scale = self._validate_torque_scale(
            self.samples_1_torque_scale
        )
        self.samples_2_torque_scale = self._validate_torque_scale(
            self.samples_2_torque_scale
        )

    @property
    def rx_pdo_size(self) -> int:
        # EL3002 is input-only in the current model.
        return 0

    @property
    def tx_pdo_size(self) -> int:
        return EL3002_TX_PDO_SIZE

    def pack_rx_pdo(self, command: El3002Command) -> bytes:
        del command
        return b""

    def unpack_tx_pdo(
        self,
        pdo: bytes,
        *,
        seq: int = 0,
        stamp_ns: int = 0,
        cycle_time_ns: int = 0,
        dc_time_error_ns: int = 0,
    ) -> El3002Data:
        del seq, stamp_ns, cycle_time_ns, dc_time_error_ns

        values: dict[str, Any] = {field.name: 0 for field in EL3002_TX_PDO_FIELDS}
        for field in EL3002_TX_PDO_FIELDS:
            field_end = field.offset + field.size
            if len(pdo) < field_end:
                continue
            values[field.name] = int.from_bytes(
                pdo[field.offset:field_end],
                byteorder="little",
                signed=field.signed,
            )

        return El3002Data(raw_pdo=bytes(pdo), **values)

    def _get_field_bytes(self, data: El3002Data, field_name: str) -> bytes:
        field = next(field for field in EL3002_TX_PDO_FIELDS if field.name == field_name)
        field_end = field.offset + field.size
        if len(data.raw_pdo) < field_end:
            return b""
        return data.raw_pdo[field.offset:field_end]

    def get_input_1(self, data: El3002Data) -> int:
        return data.input_1

    def get_samples_1(self, data: El3002Data) -> int:
        return data.samples_1

    def get_samples_1_raw(self, data: El3002Data) -> bytes:
        return self._get_field_bytes(data, "samples_1")

    def _get_scaled_adc_value(self, raw: bytes) -> float:
        if len(raw) < 4:
            return 0.0
        value = int.from_bytes(raw[:4], byteorder="little", signed=True)
        return value / float(1 << 23)

    @staticmethod
    def _validate_torque_scale(scale: float) -> float:
        scale = float(scale)
        if scale not in EL3002_ALLOWED_TORQUE_SCALES:
            raise ValueError(
                f"Unsupported EL3002 torque scale {scale}. "
                f"Allowed values: {EL3002_ALLOWED_TORQUE_SCALES}"
            )
        return scale

    def set_samples_1_torque_scale(self, scale: float) -> None:
        self.samples_1_torque_scale = self._validate_torque_scale(scale)

    def set_samples_2_torque_scale(self, scale: float) -> None:
        self.samples_2_torque_scale = self._validate_torque_scale(scale)

    def get_samples_1_scaled_voltage(self, data: El3002Data) -> float:
        return self._get_scaled_adc_value(self.get_samples_1_raw(data)) * 5.0

    def get_samples_1_scaled_torque(self, data: El3002Data) -> float:
        return self._get_scaled_adc_value(self.get_samples_1_raw(data)) * self.samples_1_torque_scale

    def get_timestamp(self, data: El3002Data) -> int:
        return data.timestamp

    def get_input_2(self, data: El3002Data) -> int:
        return data.input_2

    def get_samples_2(self, data: El3002Data) -> int:
        return data.samples_2

    def get_samples_2_raw(self, data: El3002Data) -> bytes:
        return self._get_field_bytes(data, "samples_2")

    def get_samples_2_scaled_voltage(self, data: El3002Data) -> float:
        return self._get_scaled_adc_value(self.get_samples_2_raw(data)) * 5.0

    def get_samples_2_scaled_torque(self, data: El3002Data) -> float:
        return self._get_scaled_adc_value(self.get_samples_2_raw(data)) * self.samples_2_torque_scale
