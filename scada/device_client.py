"""
Device client for the HMI.

Connects to ecosystem devices (PLCs and sensors) via Modbus TCP,
reads their metadata and current values. Supports both explicit target
lists and subnet scanning.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pymodbus.client import ModbusTcpClient

from .metadata import (
    METADATA_BLOCK_SIZE,
    DATA_BLOCK_START,
    AGGREGATOR_BLOCK_START,
    PROTOCOL_VERSION,
    DeviceKind,
    DataType,
    DeviceMetadata,
    decode_metadata,
    decode_data_value,
    _unpack_ascii,
)

logger = logging.getLogger(__name__)


@dataclass
class DeviceState:
    """Complete snapshot of a discovered device."""
    ip: str
    metadata: DeviceMetadata
    value: Any = None
    last_read: float = 0.0
    online: bool = True
    error_count: int = 0

    @property
    def tag(self) -> str:
        return self.metadata.tag

    @property
    def is_plc(self) -> bool:
        return self.metadata.device_kind == DeviceKind.PLC

    @property
    def stale(self) -> bool:
        if self.last_read == 0:
            return True
        return (time.time() - self.last_read) > (self.metadata.poll_hint_ms / 1000.0) * 5


class DeviceClient:
    """Manages connections to all discovered devices."""

    def __init__(self, targets: List[str] = None, subnets: List[str] = None,
                 timeout: float = 1.0, poll_timeout: float = 2.0, max_workers: int = 32):
        self.targets = targets or []
        self.subnets = subnets or []
        self.timeout = timeout            # Short timeout for discovery scan
        self.poll_timeout = poll_timeout   # Longer timeout for polling known devices
        self.max_workers = max_workers
        self.devices: Dict[str, DeviceState] = {}  # keyed by tag
        self._ip_to_tag: Dict[str, str] = {}

    def discover(self) -> Dict[str, DeviceState]:
        """Discover new devices without disrupting existing ones."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        ips = set()

        # Explicit targets
        for t in self.targets:
            ips.add(t.strip())

        # Subnet scanning
        for subnet_str in self.subnets:
            try:
                subnet = ipaddress.IPv4Network(subnet_str.strip(), strict=False)
                logger.info("Scanning %s ...", subnet)
                for host in subnet.hosts():
                    ips.add(str(host))
            except ValueError as e:
                logger.warning("Invalid subnet %s: %s", subnet_str, e)

        # Skip IPs we already know about — don't disrupt existing devices
        known_ips = set(self._ip_to_tag.keys())
        new_ips = ips - known_ips

        if not new_ips:
            logger.info("Discovery complete: no new IPs to probe (%d device(s) already known)", len(self.devices))
            return self.devices

        # Scan only unknown IPs in parallel
        new_count = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(self._probe, ip): ip for ip in sorted(new_ips)}
            for future in as_completed(futures):
                device = future.result()
                if device:
                    self.devices[device.tag] = device
                    self._ip_to_tag[device.ip] = device.tag
                    new_count += 1

        logger.info("Discovery complete: %d new device(s), %d total", new_count, len(self.devices))
        return self.devices

    def poll_all(self) -> None:
        """Read current values from discovered PLCs and sensors.

        For the segmented architecture, SCADA should not require direct access
        to the field/sensor LAN. PLC devices expose an aggregate child table
        starting at AGGREGATOR_BLOCK_START and live child values starting at
        DATA_BLOCK_START. When a PLC is discovered, SCADA reads that aggregate
        table and creates/updates virtual sensor DeviceState entries from the
        PLC values.
        """
        # Copy list because polling PLCs may add/update virtual sensor entries.
        for tag, device in list(self.devices.items()):
            if device.is_plc:
                try:
                    self._poll_plc_aggregate(device)
                    device.online = True
                    device.error_count = 0
                    device.last_read = time.time()
                except Exception as e:
                    device.error_count += 1
                    if device.error_count > 3:
                        device.online = False
                    logger.debug("PLC aggregate poll error for %s: %s", tag, e)
                continue

            # Direct sensor polling remains as a fallback for old/flat lab topologies.
            # Virtual PLC-sourced sensor entries use ip=<PLC IP>, so skip direct polling
            # for them; they are updated by _poll_plc_aggregate above.
            if getattr(device, "source_plc", None):
                continue

            try:
                value = self._read_value(device)
                if value is not None:
                    device.value = value
                    device.last_read = time.time()
                    device.online = True
                    device.error_count = 0
                else:
                    device.error_count += 1
                    if device.error_count > 3:
                        device.online = False
            except Exception as e:
                device.error_count += 1
                if device.error_count > 3:
                    device.online = False
                logger.debug("Poll error for %s: %s", tag, e)

    def _infer_units(self, tag: str, data_type: DataType) -> str:
        prefix = tag.split("-", 1)[0].upper()
        if prefix == "FT":
            return "GPM"
        if prefix == "LT":
            return "%"
        if prefix == "DP":
            return "psi"
        if prefix == "DO":
            return "mg/L"
        if prefix == "PH":
            return "pH"
        if prefix in ("TSS", "MLSS"):
            return "mg/L"
        if prefix == "P" or data_type == DataType.BOOL:
            return "state"
        return ""

    def _decode_signed_u16(self, value: int) -> int:
        value = int(value) & 0xFFFF
        return value - 0x10000 if value >= 0x8000 else value

    def _poll_plc_aggregate(self, plc: DeviceState) -> None:
        """Read child sensor values from a PLC aggregate table.

        PLC register layout uses zero-based Modbus addressing internally. The
        SCADA client uses pymodbus directly, so it reads zero-based addresses:
          AGGREGATOR_BLOCK_START = 50   -> sensor count
          DATA_BLOCK_START       = 100  -> four-register slots per child

        Each child index entry is 10 registers:
          8 regs tag, 1 reg data_type, 1 reg data_offset
        For FLOAT32 values, the current PLC also publishes an Ignition-friendly
        scaled x10 integer at data_offset + 2. SCADA converts that back to a
        float so dashboards show engineering values without direct sensor LAN
        access.
        """
        client = ModbusTcpClient(plc.ip, port=502, timeout=self.poll_timeout)
        try:
            if not client.connect():
                raise ConnectionError(f"Could not connect to PLC {plc.tag} at {plc.ip}:502")

            count_result = client.read_holding_registers(address=AGGREGATOR_BLOCK_START, count=1)
            if count_result.isError():
                raise RuntimeError(f"Could not read PLC aggregate count from {plc.tag}")
            count = int(count_result.registers[0])
            if count <= 0:
                logger.debug("PLC %s reports no child devices", plc.tag)
                return
            if count > 128:
                logger.warning("PLC %s reported unreasonable child count %s; ignoring", plc.tag, count)
                return

            index_result = client.read_holding_registers(
                address=AGGREGATOR_BLOCK_START + 1,
                count=count * 10,
            )
            if index_result.isError():
                raise RuntimeError(f"Could not read PLC aggregate index from {plc.tag}")

            index_regs = index_result.registers
            for idx in range(count):
                base = idx * 10
                child_tag = _unpack_ascii(index_regs[base:base + 8], 16).strip()
                if not child_tag:
                    continue

                try:
                    data_type = DataType(index_regs[base + 8])
                except Exception:
                    data_type = DataType.UINT16
                data_offset = int(index_regs[base + 9])

                slot_result = client.read_holding_registers(address=data_offset, count=4)
                if slot_result.isError():
                    continue
                slot = list(slot_result.registers) + [0, 0, 0, 0]

                if data_type == DataType.FLOAT32:
                    # PLC exposes scaled x10 at slot + 2 for Ignition/SCADA friendliness.
                    value = self._decode_signed_u16(slot[2]) / 10.0
                    reg_count = 1
                elif data_type == DataType.BOOL:
                    value = bool(slot[0])
                    reg_count = 1
                elif data_type == DataType.INT16:
                    value = self._decode_signed_u16(slot[0])
                    reg_count = 1
                else:
                    value = int(slot[0])
                    reg_count = 1

                meta = DeviceMetadata(
                    protocol_version=PROTOCOL_VERSION,
                    device_kind=DeviceKind.ACTUATOR if child_tag.upper().startswith("P-") else DeviceKind.SENSOR,
                    device_class=child_tag.split("-", 1)[0].upper(),
                    tag=child_tag,
                    units=self._infer_units(child_tag, data_type),
                    data_type=DataType.FLOAT32 if data_type == DataType.FLOAT32 else data_type,
                    data_reg_count=reg_count,
                    data_reg_start=data_offset,
                    poll_hint_ms=plc.metadata.poll_hint_ms,
                    writable=False,
                    description=f"{child_tag} via {plc.tag}",
                )

                state = self.devices.get(child_tag)
                if state is None or state.is_plc:
                    state = DeviceState(ip=plc.ip, metadata=meta)
                    # Dynamic attribute to identify PLC-backed virtual sensors.
                    setattr(state, "source_plc", plc.tag)
                    self.devices[child_tag] = state
                else:
                    state.metadata = meta
                    state.ip = plc.ip
                    setattr(state, "source_plc", plc.tag)

                state.value = value
                state.last_read = time.time()
                state.online = True
                state.error_count = 0

        finally:
            try:
                client.close()
            except Exception:
                pass

    def get_sensors_by_subnet(self) -> Dict[str, List[DeviceState]]:
        """Group non-PLC devices by their source PLC or subnet."""
        groups: Dict[str, List[DeviceState]] = {}
        plc_names: Dict[str, str] = {}

        # First pass: identify PLCs and their subnets for legacy direct sensors.
        for device in self.devices.values():
            ip_parts = device.ip.rsplit(".", 1)
            subnet_prefix = ip_parts[0]
            if device.is_plc:
                plc_names[subnet_prefix] = device.tag

        # Second pass: group PLC-backed virtual sensors under their source PLC.
        for device in self.devices.values():
            if device.is_plc:
                continue
            source_plc = getattr(device, "source_plc", None)
            if source_plc:
                plc_name = source_plc
            else:
                ip_parts = device.ip.rsplit(".", 1)
                subnet_prefix = ip_parts[0]
                plc_name = plc_names.get(subnet_prefix, f"Unknown ({subnet_prefix})")
            if plc_name not in groups:
                groups[plc_name] = []
            groups[plc_name].append(device)

        # Sort sensors within each group by tag.
        for plc_name in groups:
            groups[plc_name].sort(key=lambda d: d.tag)

        return groups

    def _probe(self, ip: str) -> Optional[DeviceState]:
        """Try to read metadata from a single IP."""
        client = ModbusTcpClient(ip, port=502, timeout=self.timeout)
        try:
            if not client.connect():
                return None
            result = client.read_holding_registers(address=0, count=METADATA_BLOCK_SIZE)
            if result.isError():
                return None
            meta = decode_metadata(result.registers)
            if meta.protocol_version != PROTOCOL_VERSION:
                return None
            if not meta.is_valid():
                return None

            logger.info("Found %s (%s) @ %s [%s]",
                        meta.tag, meta.description, ip, meta.device_kind.name)
            return DeviceState(ip=ip, metadata=meta)
        except Exception:
            return None
        finally:
            try:
                client.close()
            except Exception:
                pass

    def _read_value(self, device: DeviceState) -> Optional[Any]:
        """Read the current data value from a device."""
        meta = device.metadata
        client = ModbusTcpClient(device.ip, port=502, timeout=self.poll_timeout)
        try:
            if not client.connect():
                return None
            result = client.read_holding_registers(
                address=meta.data_reg_start,
                count=meta.data_reg_count,
            )
            if result.isError():
                return None
            return decode_data_value(result.registers, meta.data_type)
        except Exception:
            return None
        finally:
            try:
                client.close()
            except Exception:
                pass

    # --- Sensor control (write operations) ---


    # --- PLC logic API helpers ---

    def get_plcs(self) -> List[DeviceState]:
        """Return discovered PLC devices sorted by tag."""
        return sorted([d for d in self.devices.values() if d.is_plc], key=lambda d: d.tag)

    def get_plc_logic(self, tag: str, timeout: float = 3.0) -> Optional[str]:
        """Read the current runtime logic YAML from a PLC's HTTP API."""
        import urllib.request

        device = self.devices.get(tag)
        if not device or not device.is_plc:
            return None
        url = f"http://{device.ip}:8080/logic"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            logger.debug("Could not read PLC logic from %s: %s", tag, e)
            return None

    def get_plc_logic_health(self, tag: str, timeout: float = 2.0) -> dict:
        """Read PLC logic API health. Returns a small status dict."""
        import json
        import urllib.request

        device = self.devices.get(tag)
        if not device or not device.is_plc:
            return {"ok": False, "error": "PLC not found"}
        url = f"http://{device.ip}:8080/health"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def upload_plc_logic(self, tag: str, content: bytes, timeout: float = 5.0) -> tuple[bool, str]:
        """Upload YAML logic to a PLC's HTTP API and trigger hot-reload."""
        import urllib.request

        device = self.devices.get(tag)
        if not device or not device.is_plc:
            return False, "PLC not found"
        url = f"http://{device.ip}:8080/logic"
        try:
            req = urllib.request.Request(
                url,
                data=content,
                headers={"Content-Type": "application/x-yaml"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return 200 <= resp.status < 300, resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            return False, str(e)

    MODE_REGISTER = 99  # 0=auto, 1=manual

    def write_sensor_mode(self, tag: str, manual: bool) -> bool:
        """Set a sensor to manual mode (1) or auto mode (0)."""
        device = self.devices.get(tag)
        if not device or device.is_plc:
            return False
        client = ModbusTcpClient(device.ip, port=502, timeout=self.poll_timeout)
        try:
            if not client.connect():
                return False
            result = client.write_registers(
                address=self.MODE_REGISTER,
                values=[1 if manual else 0],
            )
            if result.isError():
                return False
            logger.info("Set %s mode to %s", tag, "MANUAL" if manual else "AUTO")
            return True
        except Exception as e:
            logger.warning("Failed to set mode for %s: %s", tag, e)
            return False
        finally:
            try:
                client.close()
            except Exception:
                pass

    def write_sensor_value(self, tag: str, value: Any) -> bool:
        """Write a value to a sensor's data registers (use with manual mode)."""
        device = self.devices.get(tag)
        if not device or device.is_plc:
            return False
        meta = device.metadata
        from .metadata import encode_data_value
        try:
            regs = encode_data_value(value, meta.data_type, meta.data_reg_count)
        except Exception as e:
            logger.warning("Failed to encode value for %s: %s", tag, e)
            return False
        client = ModbusTcpClient(device.ip, port=502, timeout=self.poll_timeout)
        try:
            if not client.connect():
                return False
            result = client.write_registers(address=meta.data_reg_start, values=regs)
            if result.isError():
                return False
            logger.info("Wrote %s = %s", tag, value)
            return True
        except Exception as e:
            logger.warning("Failed to write %s: %s", tag, e)
            return False
        finally:
            try:
                client.close()
            except Exception:
                pass

    def read_sensor_mode(self, tag: str) -> Optional[int]:
        """Read a sensor's current mode (0=auto, 1=manual)."""
        device = self.devices.get(tag)
        if not device or device.is_plc:
            return None
        client = ModbusTcpClient(device.ip, port=502, timeout=self.poll_timeout)
        try:
            if not client.connect():
                return None
            result = client.read_holding_registers(address=self.MODE_REGISTER, count=1)
            if result.isError():
                return None
            return result.registers[0]
        except Exception:
            return None
        finally:
            try:
                client.close()
            except Exception:
                pass
/app #

