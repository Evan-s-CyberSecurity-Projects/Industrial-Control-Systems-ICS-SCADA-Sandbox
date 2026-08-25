# Industrial Control Systems (ICS) & SCADA Sandbox

A reproducible virtual **Industrial Control Systems (ICS) / Operational Technology (OT) laboratory** built with **GNS3, Docker, Python, Modbus TCP, simulated PLCs, HMIs, SCADA, and CI/CD automation**.

This project simulates a small wastewater treatment facility and provides an isolated environment for studying:

* OT/ICS network architecture
* SCADA and PLC communications
* Modbus TCP
* Industrial device discovery
* Network segmentation
* Linux networking
* Protocol troubleshooting
* GNS3 API automation
* Infrastructure reproducibility
* Cybersecurity testing in an isolated laboratory

> **Portfolio Notice:** This repository is a sanitized, independent portfolio version of the laboratory. University-specific infrastructure, credentials, internal server information, and other environment-specific materials have been intentionally removed.

---

## Overview

The goal of this project is to build a realistic but fully virtualized ICS environment that can be **deployed, tested, and rebuilt programmatically**.

The simulated facility is divided into seven process areas. Each process area contains a PLC and a collection of simulated field devices. HMIs and a centralized SCADA system communicate with the PLCs over a dedicated control network.

The environment is deployed through the **GNS3 API**, allowing the topology to be created consistently without manually recreating every node, interface, and connection.

The result is a repeatable cyber-range-style environment suitable for:

* ICS/OT security research
* Network and protocol analysis
* SCADA troubleshooting
* Industrial protocol experimentation
* Defensive security testing
* Red-team/blue-team laboratory exercises

---

## Architecture

```text
                               ┌─────────────────────┐
                               │        SCADA        │
                               │                     │
                               │  Web Dashboard      │
                               │  Device Discovery   │
                               │  Historian / API    │
                               └──────────┬──────────┘
                                          │
                              SCADA / Control Network
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              │                           │                           │
          ┌───▼────┐                  ┌───▼────┐                  ┌───▼────┐
          │  PLC   │                  │  PLC   │                  │  PLC   │
          │Process │                  │Process │                  │Process │
          │   A    │                  │   B    │                  │   C    │
          └───┬────┘                  └───┬────┘                  └───┬────┘
              │                           │                           │
        Process Network             Process Network             Process Network
              │                           │                           │
       ┌──────┴──────┐             ┌──────┴──────┐             ┌──────┴──────┐
       │   Sensors   │             │   Sensors   │             │   Sensors   │
       │ Actuators   │             │ Actuators   │             │ Actuators   │
       └─────────────┘             └─────────────┘             └─────────────┘
              │                           │                           │
             HMI                         HMI                         HMI

                                  +
                              Kali Linux
                          Security Workstation
```

The complete environment contains seven simulated process areas:

| Process Area  | PLC               | Example Field Devices                        |
| ------------- | ----------------- | -------------------------------------------- |
| Influent      | PLC-Influent      | Flow, level, differential pressure, pump     |
| Primary       | PLC-Primary       | Flow, level, differential pressure, mixer    |
| Aeration      | PLC-Aeration      | Dissolved oxygen, flow, MLSS, blower         |
| Clarification | PLC-Clarification | Flow, level, turbidity, dosing               |
| Disinfection  | PLC-Disinfection  | Chlorine, flow, level, valve                 |
| Thickening    | PLC-Thickening    | Level, sludge flow, solids, pump             |
| Digestion     | PLC-Digestion     | Temperature, pressure, gas flow, biogas flow |

---

## Technology Stack

| Technology                 | Role                                                 |
| -------------------------- | ---------------------------------------------------- |
| **GNS3**                   | Virtual network and topology simulation              |
| **Docker**                 | Lightweight PLC, HMI, sensor, and SCADA nodes        |
| **Python**                 | Infrastructure automation and application logic      |
| **gns3fy**                 | GNS3 API integration                                 |
| **Modbus TCP**             | PLC/SCADA communications                             |
| **Flask**                  | SCADA web application                                |
| **Jenkins**                | Automated deployment and build orchestration         |
| **Linux networking tools** | Interface, routing, and connectivity troubleshooting |
| **Wireshark**              | Industrial traffic and protocol analysis             |

---

# SCADA System

The SCADA platform provides a centralized interface for monitoring and interacting with the simulated process environment.

Core functionality includes:

* Automatic PLC discovery
* Modbus TCP communications
* Metadata-based device identification
* PLC aggregate sensor tables
* Live process values
* Alarm and status evaluation
* Historian functionality
* Trend and reporting functionality
* Sensor control
* Manual/automatic operating modes
* PLC logic management
* Live process visualization

### Device Discovery

The SCADA system uses a **self-describing metadata contract** implemented through a defined Modbus register block.

Rather than requiring every PLC to be manually configured in the SCADA application, the SCADA server can interrogate a PLC, validate its metadata, identify the device, and determine how its process data should be interpreted.

```text
SCADA
  │
  │ Modbus TCP
  ▼
PLC Metadata Block
  │
  ├── Protocol Version
  ├── Device Type
  ├── Device Class
  ├── Device Tag
  └── Data Configuration
  │
  ▼
Device Validated
  │
  ▼
PLC Aggregate Table
  │
  ├── Sensor 1
  ├── Sensor 2
  ├── Sensor 3
  └── ...
  │
  ▼
Live SCADA Data
```

The final test environment successfully established Modbus communication with **all seven simulated PLCs** and demonstrated automatic device discovery.

---

# Network Architecture

The laboratory separates the simulated industrial environment into multiple logical network segments.

Each PLC uses separate interfaces for:

1. **Process/field communications**
2. **SCADA/HMI communications**

This architecture makes it possible to study concepts including:

* OT network segmentation
* Multi-interface PLCs
* Process-to-SCADA communications
* Interface selection
* Routing behavior
* Network isolation
* Industrial protocol exposure
* Attack surface reduction

All addresses shown in this repository are laboratory examples and do not represent production infrastructure.

---

# Automated Deployment

One of the primary goals of the project is **reproducibility**.

Instead of manually building a large GNS3 topology, the environment can be generated through the GNS3 API.

The deployment automation is responsible for creating and configuring:

1. The GNS3 project
2. Network switches and segments
3. PLCs
4. HMIs
5. SCADA infrastructure
6. Sensors and actuators
7. Network interfaces
8. Device-to-device links
9. Docker network configuration
10. Device startup and validation

### Deployment Flow

```text
                    Jenkins
                       │
                       ▼
                Python Build Logic
                       │
                       ▼
                    GNS3 API
                       │
        ┌──────────────┼──────────────┐
        │              │              │
     Create          Configure       Link
     Nodes           Interfaces     Devices
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                 Start Devices
                       │
                       ▼
              Connectivity Checks
                       │
                       ▼
                Operational Lab
```

This approach significantly reduces manual configuration and makes topology deployments more consistent.

---

# Validation & Troubleshooting

A major part of the project involved troubleshooting the environment from the **network layer upward** rather than assuming that application failures were caused by the application itself.

The troubleshooting process included independent validation of:

```text
Physical / Virtual Topology
          ↓
Network Interfaces
          ↓
Routing
          ↓
TCP Connectivity
          ↓
Modbus TCP
          ↓
PLC Metadata
          ↓
SCADA Device Discovery
          ↓
SCADA Application
          ↓
Web Interface
```

This layered approach was particularly useful when different components appeared to be failing simultaneously.

---

## Layer 3 Networking

Multiple interfaces and segmented process networks required verification of Linux interface configuration and routing behavior.

Common diagnostic commands included:

```bash
ip addr
ip route
ss -lntp
ping <host>
```

These tests were used to distinguish basic network problems from higher-level protocol and application issues.

---

## Modbus TCP Validation

Each PLC was tested independently over **TCP port 502**.

This allowed PLC connectivity to be verified before involving the SCADA application.

The final environment successfully established Modbus TCP connectivity with all seven PLCs.

---

## Metadata Validation

The PLC metadata block was independently tested to verify:

* Register count
* Protocol version
* Device type
* Device class
* Device tag
* Data configuration
* Metadata validity

This proved especially useful when diagnosing SCADA discovery failures.

---

## SCADA Discovery Debugging

The SCADA `DeviceClient` was tested independently from the web dashboard.

This allowed network, protocol, metadata, and application problems to be separated instead of troubleshooting the entire stack simultaneously.

One of the more important debugging findings involved a mismatch between the number of registers expected by the metadata contract and the number requested by the SCADA probing logic.

The issue was isolated by querying the PLC directly and validating the metadata block independently of the dashboard.

This demonstrated a useful troubleshooting principle:

> **Validate each layer independently before modifying the layer above it.**

---

## Application vs. Console Availability

Another issue encountered during development involved distinguishing:

```text
SCADA Application Availability
             vs.
GNS3 Console / Proxy Availability
```

The SCADA application could be reachable from within its container while the GNS3 console path was experiencing a separate problem.

This reinforced the importance of testing application services independently from the infrastructure used to access them.

---

# Security Research Use

The environment is designed to provide a safe place for experimentation with industrial networks.

Possible laboratory exercises include:

* Network reconnaissance
* Modbus TCP enumeration
* Industrial protocol analysis
* SCADA asset discovery
* Packet capture and traffic analysis
* PLC communication testing
* Network segmentation validation
* Detection engineering
* Defensive monitoring
* Controlled attack/defense scenarios

A dedicated security workstation can be connected to the simulated control network for authorized testing inside the isolated lab.

---

# Screenshots

Screenshots demonstrating the environment are available in the [`Screenshots`](./Screenshots) directory.

Recommended examples include:

* GNS3 topology
* SCADA dashboard
* PLC discovery results
* Modbus communications
* Network configuration
* Deployment output
* Validation/testing results

---

# Repository Structure

```text
.
├── README.md
├── Screenshots/
├── Topology/
├── SCADA/
├── Devices/
├── Docker/
├── Jenkins/
└── docs/
```

The repository structure may evolve as the project is further modularized and documented.

---

# Security & Privacy

This repository is intended for public portfolio use.

The public version should never contain:

* Credentials
* API keys
* Access tokens
* VPN configuration
* Internal server addresses
* Private infrastructure details
* Production network information
* University-specific infrastructure information
* Proprietary course materials
* Private deployment configuration

Environment-specific configuration should be supplied through environment variables or local configuration files excluded from version control.

A `.gitignore` file should be used to prevent accidental publication of secrets and local configuration.

---

# Future Development

Potential extensions include:

* Additional simulated process areas
* More advanced PLC control logic
* Expanded Modbus functionality
* IDS/IPS integration
* Automated packet-capture analysis
* Security monitoring and alerting
* Automated security validation
* CI-based topology testing
* Automated deployment health checks
* Expanded historian and analytics capabilities
* More realistic process simulation
* Repeatable red-team/blue-team scenarios
* Automated attack detection and response exercises

---

# Project Goals

The project is built around three core engineering goals:

### Reproducibility

The entire environment should be capable of being rebuilt through automation rather than manual configuration.

### Observability

Failures should be diagnosable from the network layer through the industrial protocol and application layers.

### Security

The laboratory should provide an isolated environment for understanding and testing the security characteristics of ICS/SCADA systems.

---

# Disclaimer

This project is intended for **education, experimentation, cybersecurity research, and defensive security testing in isolated laboratory environments**.

It is not intended for deployment against real industrial control systems, production networks, or infrastructure without explicit authorization.
