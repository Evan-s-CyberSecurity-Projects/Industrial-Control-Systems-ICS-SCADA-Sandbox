# Industrial Control Systems (ICS) & SCADA Sandbox

A virtual Industrial Control Systems (ICS) laboratory built with **GNS3, Docker, Modbus TCP, simulated PLCs, HMIs, SCADA, and automated topology deployment**.

This project provides an isolated environment for exploring OT/ICS networking, industrial protocols, SCADA architecture, device discovery, network segmentation, monitoring, and troubleshooting.

> **Note:** This repository is a sanitized portfolio version of the lab. Internal infrastructure details, credentials, and university-specific materials are intentionally excluded.

## Project Overview

The goal of this project is to simulate a small wastewater treatment facility as a realistic OT environment.

The laboratory contains multiple process areas, each represented by a PLC, HMI, and collection of field devices. The PLCs communicate with a centralized SCADA system using **Modbus TCP**, while the SCADA platform automatically discovers PLCs and retrieves process values from their aggregate data tables.

The topology is generated and deployed programmatically through the **GNS3 API**, allowing the environment to be rebuilt consistently instead of manually recreating every device and connection.

## Architecture

```text
                         ┌─────────────────────┐
                         │      SCADA          │
                         │  Process Dashboard  │
                         │ Historian / API     │
                         └──────────┬──────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
         Process VLANs          Process VLANs          Process VLANs
             │                      │                      │
        ┌────▼────┐            ┌────▼────┐            ┌────▼────┐
        │   PLC   │            │   PLC   │            │   PLC   │
        └────┬────┘            └────┬────┘            └────┬────┘
             │                      │                      │
       ┌─────┴─────┐          ┌─────┴─────┐          ┌─────┴─────┐
       │ Field     │          │ Field     │          │ Field     │
       │ Devices   │          │ Devices   │          │ Devices   │
       └───────────┘          └───────────┘          └───────────┘
             │                      │                      │
           HMI                    HMI                    HMI
```

The complete environment contains seven simulated process areas:

| Process Area  | PLC               | Example Field Devices                        |
| ------------- | ----------------- | -------------------------------------------- |
| Influent      | PLC-Influent      | Flow, level, differential pressure, pump     |
| Primary       | PLC-Primary       | Flow, level, differential pressure, mixer    |
| Aeration      | PLC-Aeration      | Dissolved oxygen, flow, MLSS, blower         |
| Clarification | PLC-Clarification | Flow, level, turbidity, dosing               |
| Disinfection  | PLC-Disenfection  | Chlorine, flow, level, valve                 |
| Thickening    | PLC-Thickening    | Level, sludge flow, solids, pump             |
| Digestion     | PLC-Digestion     | Temperature, pressure, gas flow, biogas flow |

## Technologies

* **GNS3** — virtual network and topology simulation
* **Docker** — lightweight PLC, HMI, sensor, and SCADA nodes
* **Python** — topology automation and SCADA application logic
* **gns3fy** — GNS3 API automation
* **Modbus TCP** — PLC communications
* **Flask** — SCADA web application
* **Jenkins** — automated topology deployment
* **Linux networking tools** — interface, routing, and connectivity troubleshooting
* **Wireshark** — industrial traffic analysis

## SCADA System

The SCADA platform provides:

* Automatic PLC discovery
* Modbus TCP communication
* Metadata-based device identification
* PLC aggregate sensor tables
* Live process values
* Alarm/status evaluation
* Historian functionality
* Trend and reporting functionality
* Sensor control and manual/automatic modes
* PLC logic management
* A live process visualization dashboard

The SCADA discovery process uses a self-describing metadata contract. PLCs expose metadata through a defined Modbus register block, allowing the SCADA server to identify devices and determine how their process data should be interpreted.

### Example Discovery Flow

```text
SCADA
  │
  ├── Modbus TCP connection
  │
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
PLC Discovered
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
Live SCADA Values
```

## Network Segmentation

The laboratory separates process networks into individual logical segments.

Each PLC maintains a process-facing interface for its field devices and a separate interface for communication with the SCADA/HMI network.

This allows the lab to demonstrate concepts such as:

* OT network segmentation
* Multi-interface PLCs
* Process-to-SCADA communication
* Management/out-of-band networking
* Routing and interface selection
* Network isolation
* Industrial protocol exposure

All addresses shown in public documentation are representative examples rather than live infrastructure addresses.

## Automation

The topology can be generated programmatically through the GNS3 API.

The build process creates:

1. Process devices
2. VLAN/switch segments
3. PLCs
4. HMIs
5. SCADA infrastructure
6. Field sensors and actuators
7. Network interfaces
8. Links between devices
9. Docker network configurations

This makes the environment reproducible and dramatically reduces manual GNS3 configuration.

### Automation Flow

```text
Jenkins
   │
   ▼
Python Build Script
   │
   ▼
GNS3 API
   │
   ├── Create Project
   ├── Create Nodes
   ├── Configure Interfaces
   ├── Create Links
   └── Start Devices
   │
   ▼
Operational ICS Laboratory
```

## Troubleshooting & Engineering Lessons

One of the primary goals of the project was learning how to troubleshoot the system from the bottom of the stack upward.

Examples of issues investigated during development included:

### Layer 3 Routing

Multiple interfaces and segmented process networks required careful verification of interface addresses and routing tables.

Useful commands included:

```bash
ip addr
ip route
ss -lntp
```

### Modbus Connectivity

Rather than assuming the SCADA application was broken, each PLC was independently tested over TCP port 502.

The final environment successfully established Modbus connectivity to all seven PLCs.

### Metadata Validation

The PLC metadata block was tested independently to verify:

* Correct register count
* Protocol version
* Device type
* Device tag
* Data configuration
* Metadata validity

### SCADA Discovery

The SCADA `DeviceClient` was tested independently from the web application to distinguish network/protocol failures from application-layer failures.

This made it possible to isolate problems without repeatedly modifying the topology.

### HTTP / GNS3 Console Debugging

The SCADA application could be accessed successfully from inside the container, while the GNS3 HTTP console required separate troubleshooting.

This highlighted an important distinction between:

```text
Application availability
        vs.
GNS3 console/proxy availability
```

## Screenshots

Screenshots of the topology, SCADA dashboard, and testing process are available in the [`Screenshots`](./Screenshots) directory.

## Repository Structure

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

The exact structure may evolve as the project is cleaned up and documented for public use.

## Security Considerations

This project is intended as an **isolated educational ICS/SCADA environment**.

Public repository contents should not contain:

* Real credentials
* API keys or tokens
* Internal university infrastructure addresses
* VPN configuration
* Production network information
* Private server details
* Course-provided proprietary materials

Environment-specific values should be supplied through environment variables or local configuration files that are excluded from version control.

## Future Improvements

Potential extensions include:

* Adding additional simulated process areas
* Expanding Modbus functionality
* Adding IDS/IPS monitoring
* Integrating packet-capture analysis into the lab
* Adding automated security testing
* Building CI validation for topology changes
* Adding automated health checks
* Expanding historian and analytics functionality
* Adding more realistic PLC control logic
* Creating repeatable attack/defense scenarios

## Disclaimer

This project is intended for **education, experimentation, and defensive security research in isolated laboratory environments**.

It is not intended for deployment against real industrial control systems or production infrastructure.
