# SCADA

This directory contains the SCADA application used to monitor and interact with the simulated ICS environment.

The application communicates with the laboratory PLCs over **Modbus TCP** and provides automatic device discovery, process monitoring, alarms, historical data, and a web-based visualization interface.

## Core Functions

The SCADA system provides:

* Automatic PLC discovery
* Modbus TCP communications
* Metadata-based device identification
* Aggregate PLC sensor tables
* Live process values
* Alarm and status monitoring
* Historical process data
* Trend visualization
* Manual and automatic control modes
* PLC logic interaction
* Web-based process visualization

## Device Discovery

SCADA does not require every PLC to be manually defined.

Each simulated PLC exposes a structured metadata block through Modbus TCP. The SCADA client reads and validates this metadata before identifying the device and interpreting its process data.

```text
SCADA
  │
  │ Modbus TCP
  ▼
PLC Metadata
  │
  ├── Protocol Version
  ├── Device Type
  ├── Device Class
  ├── Device Tag
  └── Data Configuration
  │
  ▼
PLC Identified
  │
  ▼
Aggregate Process Data
  │
  ▼
SCADA Dashboard
```

The completed laboratory demonstrates automatic discovery of seven simulated process PLCs.

## Communication Model

The SCADA server communicates with the PLC control interfaces using Modbus TCP.

Field devices are not required to communicate directly with SCADA. Instead, PLCs collect and expose process information to the supervisory layer.

```text
Field Devices
      │
      ▼
     PLC
      │
      ▼
    SCADA
```

This provides a simplified model of the supervisory relationship between field controllers and a centralized SCADA platform.

## Troubleshooting

The SCADA implementation was developed and debugged independently from the underlying GNS3 topology.

Failures were isolated progressively across:

```text
Network Connectivity
        ↓
TCP / Modbus
        ↓
PLC Metadata
        ↓
Device Discovery
        ↓
SCADA Application
        ↓
Web Interface
```

This approach made it possible to distinguish protocol and networking problems from SCADA application problems.

## Security Research

The SCADA environment is intended for isolated laboratory experimentation.

It can be used to study:

* Industrial protocol communications
* PLC asset discovery
* Modbus TCP traffic
* SCADA monitoring
* Alarm behavior
* Network security controls
* Defensive detection techniques

All security testing should remain within the authorized laboratory environment.
