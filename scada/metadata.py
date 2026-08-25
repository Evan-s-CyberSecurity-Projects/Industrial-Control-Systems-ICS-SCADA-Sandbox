"""
Metadata contract parsing.

Encodes and decodes the 40-register metadata block defined in
METADATA_CONTRACT.md. Used by both discovery (reading sensor metadata)
and the PLC's own Modbus server (publishing its own metadata).

This module has zero scenario knowledge. It just reads and writes bytes.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List


PROTOCOL_VERSION = 1
METADATA_BLOCK_SIZE = 40
DATA_BLOCK_START = 100
AGGREGATOR_BLOCK_START = 50


class DeviceKind(IntEnum):
    UNKNOWN = 0
    SENSOR = 1
    ACTUATOR = 2
    PLC = 3
    HMI = 4


class DataType(IntEnum):
    BOOL = 0
    INT16 = 1
    UINT16 = 2
    FLOAT32 = 3
    ASCII = 4


@dataclass
class DeviceMetadata:
    """Self-describing metadata read from any ecosystem device."""

    protocol_version: int = PROTOCOL_VERSION
    device_kind: DeviceKind = DeviceKind.UNKNOWN
    device_class: str = ""
    tag: str = ""
    units: str = ""
    data_type: DataType = DataType.UINT16
    data_reg_count: int = 1
    data_reg_start: int = DATA_BLOCK_START
    poll_hint_ms: int = 1000
    writable: bool = False
    description: str = ""

    def is_valid(self) -> bool:
        return self.protocol_version == PROTOCOL_VERSION and bool(self.tag.strip())


def _pack_ascii(text: str, char_count: int) -> List[int]:
    """Pack ASCII string into register list (2 chars per register, space-padded)."""
    padded = text.ljust(char_count)[:char_count]
    registers = []
    for i in range(0, char_count, 2):
        hi = ord(padded[i]) if i < len(padded) else 0x20
        lo = ord(padded[i + 1]) if i + 1 < len(padded) else 0x20
        registers.append((hi << 8) | lo)
    return registers


def _unpack_ascii(registers: List[int], char_count: int) -> str:
    """Unpack register list back to ASCII string, stripped."""
    chars = []
    reg_count = (char_count + 1) // 2
    for reg in registers[:reg_count]:
        chars.append(chr((reg >> 8) & 0xFF))
        chars.append(chr(reg & 0xFF))
    return "".join(chars)[:char_count].rstrip()


def encode_metadata(meta: DeviceMetadata) -> List[int]:
    """Encode metadata into a 40-register block."""
    regs = [0] * METADATA_BLOCK_SIZE
    regs[0] = meta.protocol_version
    regs[1] = int(meta.device_kind)
    regs[2:4] = _pack_ascii(meta.device_class, 4)
    regs[4:12] = _pack_ascii(meta.tag, 16)
    regs[12:20] = _pack_ascii(meta.units, 16)
    regs[20] = int(meta.data_type)
    regs[21] = meta.data_reg_count
    regs[22] = meta.data_reg_start
    regs[23] = meta.poll_hint_ms
    regs[24] = 1 if meta.writable else 0
    regs[25:40] = _pack_ascii(meta.description, 30)
    return regs


def decode_metadata(registers: List[int]) -> DeviceMetadata:
    """Decode a 40-register block into metadata."""
    if len(registers) < METADATA_BLOCK_SIZE:
        raise ValueError(f"Need {METADATA_BLOCK_SIZE} registers, got {len(registers)}")

    return DeviceMetadata(
        protocol_version=registers[0],
        device_kind=DeviceKind(registers[1]) if registers[1] in DeviceKind._value2member_map_ else DeviceKind.UNKNOWN,
        device_class=_unpack_ascii(registers[2:4], 4),
        tag=_unpack_ascii(registers[4:12], 16),
        units=_unpack_ascii(registers[12:20], 16),
        data_type=DataType(registers[20]) if registers[20] in DataType._value2member_map_ else DataType.UINT16,
        data_reg_count=registers[21],
        data_reg_start=registers[22],
        poll_hint_ms=registers[23],
        writable=bool(registers[24]),
        description=_unpack_ascii(registers[25:40], 30),
    )


def decode_data_value(registers: List[int], data_type: DataType):
    """Decode a data-block payload into a Python value."""
    if data_type == DataType.BOOL:
        return bool(registers[0])
    if data_type == DataType.INT16:
        val = registers[0]
        return val - 0x10000 if val >= 0x8000 else val
    if data_type == DataType.UINT16:
        return registers[0]
    if data_type == DataType.FLOAT32:
        packed = struct.pack(">HH", registers[0], registers[1])
        return struct.unpack(">f", packed)[0]
    if data_type == DataType.ASCII:
        return _unpack_ascii(registers, len(registers) * 2)
    raise ValueError(f"Unknown data type: {data_type}")


def encode_data_value(value, data_type: DataType, reg_count: int = 1) -> List[int]:
    """Encode a Python value into register list per data type."""
    if data_type == DataType.BOOL:
        return [1 if value else 0]
    if data_type == DataType.INT16:
        v = int(value)
        return [v + 0x10000 if v < 0 else v]
    if data_type == DataType.UINT16:
        return [int(value) & 0xFFFF]
    if data_type == DataType.FLOAT32:
        packed = struct.pack(">f", float(value))
        hi, lo = struct.unpack(">HH", packed)
        return [hi, lo]
    if data_type == DataType.ASCII:
        return _pack_ascii(str(value), reg_count * 2)
    raise ValueError(f"Unknown data type: {data_type}")


