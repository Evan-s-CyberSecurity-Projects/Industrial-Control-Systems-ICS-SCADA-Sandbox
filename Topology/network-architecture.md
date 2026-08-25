# Network Architecture

## Overview

The ICS/SCADA Sandbox models a small wastewater treatment facility using a segmented **Operational Technology (OT)** network architecture.

The environment separates field-device communications from higher-level PLC, HMI, and SCADA communications while giving each process area its own logical network segment.

The laboratory contains seven simulated process areas:

1. Influent
2. Primary
3. Aeration
4. Clarification
5. Disinfection
6. Thickening
7. Digestion

Each process area contains:

* One process PLC
* One HMI
* Multiple simulated sensors and/or actuators
* A dedicated field-device network
* A PLC/HMI/SCADA-facing process network

A centralized SCADA server communicates with the PLCs using **Modbus TCP**.

The architecture is intentionally designed so that the PLC serves as the boundary between local field devices and higher-level control infrastructure.

---

## High-Level Architecture

```text
                         ┌─────────────────────┐
                         │       Jenkins       │
                         │ Automated Deployment│
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   Python / GNS3    │
                         │   Topology Builder  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     OT Network      │
                         │                     │
                         │  ┌───────────────┐  │
                         │  │     SCADA     │  │
                         │  └───────┬───────┘  │
                         │          │          │
                         │  ┌───────┼───────┐  │
                         │  │       │       │  │
                         │  ▼       ▼       ▼  │
                         │ PLC     PLC     PLC  │
                         │  │       │       │  │
                         │ HMI     HMI     HMI  │
                         │  │       │       │  │
                         │Field   Field   Field │
                         │ LAN     LAN     LAN  │
                         └─────────────────────┘
                                   
                              + Kali Linux
                            Security Workstation
```

The deployment and application layers are separate from the simulated industrial process itself. Jenkins invokes the topology builder, while the resulting GNS3 environment contains the SCADA, PLC, HMI, and field-device infrastructure.

---

# Process Area Segmentation

Each process area operates as an independent logical segment.

| Process Area  | Process Network | Field Network | PLC               |
| ------------- | --------------- | ------------- | ----------------- |
| Influent      | Process-A       | Field-A       | PLC-Influent      |
| Primary       | Process-B       | Field-B       | PLC-Primary       |
| Aeration      | Process-C       | Field-C       | PLC-Aeration      |
| Clarification | Process-D       | Field-D       | PLC-Clarification |
| Disinfection  | Process-E       | Field-E       | PLC-Disinfection  |
| Thickening    | Process-F       | Field-F       | PLC-Thickening    |
| Digestion     | Process-G       | Field-G       | PLC-Digestion     |

The public documentation intentionally uses **logical network names rather than environment-specific addressing**.

Actual deployment values are defined by the local laboratory configuration and are not required to understand the architecture.

This segmentation provides separate failure and troubleshooting domains while allowing each PLC to communicate upward with authorized SCADA/HMI systems.

---

# PLC Architecture

Each simulated PLC uses two logical network interfaces.

```text
                         PLC
                  ┌─────────────────┐
                  │                 │
Field Network ───►│  Field Interface│
                  │                 │
Process Network ─►│ SCADA Interface │
                  │                 │
                  └─────────────────┘
```

The **field-facing interface** communicates with local sensors and actuators.

The **process-facing interface** communicates with higher-level systems such as:

* SCADA
* HMI infrastructure
* Other authorized process-network services

This design models a common OT architecture in which the PLC separates local process communications from supervisory control traffic.

---

# Field Devices

Field devices are simulated as lightweight Docker-based nodes.

They represent sensors, measurement instruments, and actuators found within different stages of the wastewater treatment process.

## Influent

| Tag    | Function              |
| ------ | --------------------- |
| FT-101 | Flow                  |
| LT-101 | Level                 |
| DP-101 | Differential pressure |
| P-101  | Pump                  |

## Primary

| Tag    | Function              |
| ------ | --------------------- |
| FT-201 | Flow                  |
| LT-201 | Level                 |
| DP-201 | Differential pressure |
| MV-201 | Mixer                 |

## Aeration

| Tag      | Function                      |
| -------- | ----------------------------- |
| DO-301   | Dissolved oxygen              |
| FT-301   | Flow                          |
| MLSS-301 | Mixed liquor suspended solids |
| SV-301   | Blower                        |

## Clarification

| Tag    | Function  |
| ------ | --------- |
| FT-401 | Flow      |
| LT-401 | Level     |
| TU-401 | Turbidity |
| DL-401 | Dosing    |

## Disinfection

| Tag    | Function |
| ------ | -------- |
| CL-501 | Chlorine |
| FT-501 | Flow     |
| LT-501 | Level    |
| AV-501 | Valve    |

## Thickening

| Tag    | Function    |
| ------ | ----------- |
| LT-601 | Level       |
| FT-601 | Sludge flow |
| SS-601 | Solids      |
| P-601  | Pump        |

## Digestion

| Tag     | Function    |
| ------- | ----------- |
| T-701   | Temperature |
| PT-701  | Pressure    |
| FT-701  | Flow        |
| GAS-701 | Gas flow    |

---

# PLC-to-SCADA Communication

SCADA communicates with the PLCs using **Modbus TCP**.

The normal communication path is:

```text
                        SCADA
                          │
                          │ Modbus TCP
                          │ TCP/502
                          ▼
                         PLC
                          │
              ┌───────────┼───────────┐
              │           │           │
              ▼           ▼           ▼
          Metadata   Aggregate Data  Control
             Block       Table        Data
```

The SCADA client first establishes a Modbus connection with the PLC and validates the PLC's metadata.

Once the PLC has been identified, SCADA can retrieve its aggregate process data.

This avoids requiring the SCADA system to communicate independently with every simulated field device.

The resulting data path is:

```text
SCADA
  │
  ▼
PLC
  │
  ├── Field Device 1
  ├── Field Device 2
  ├── Field Device 3
  └── Actuator
```

The PLC therefore acts as the primary interface between supervisory systems and its local process devices.

---

# Metadata Architecture

The simulated PLCs expose a structured metadata block through Modbus.

The metadata describes how the device should be interpreted by the SCADA system.

Depending on the device, the metadata can include:

* Protocol version
* Device kind
* Device class
* Device tag
* Units
* Data type
* Register count
* Register starting address
* Polling information
* Writable state
* Description

The discovery workflow is:

```text
Connect to PLC
      │
      ▼
Read Metadata Block
      │
      ▼
Validate Metadata
      │
      ▼
Identify PLC
      │
      ▼
Read Aggregate Device Table
      │
      ▼
Build Device State
      │
      ▼
Poll Process Values
      │
      ▼
Update SCADA
```

This creates a **self-describing device architecture**. New PLCs can be identified and interpreted by SCADA through their metadata rather than requiring every device to be manually defined in the application.

---

# HMI Architecture

Each process area contains a dedicated HMI node.

The HMI provides a process-facing interface for interacting with and monitoring the simulated process.

The logical relationship is:

```text
                   Field Devices
                         │
                         ▼
                        PLC
                       /   \
                      /     \
                     ▼       ▼
                   HMI     SCADA
```

The HMI and SCADA systems are therefore both consumers of PLC process information.

Importantly, **HMI availability is not a prerequisite for PLC discovery by SCADA**.

This separation is useful during troubleshooting because failures in an individual HMI can be investigated independently from the underlying PLC/SCADA communications path.

---

# Security Workstation

The laboratory can include a dedicated **Kali Linux security workstation** connected to the simulated OT network.

```text
                     ┌──────────────┐
                     │   SCADA      │
                     └──────┬───────┘
                            │
                     Control Network
                            │
             ┌──────────────┼──────────────┐
             │              │              │
            PLC            PLC            PLC
             │              │              │
          Field LAN      Field LAN      Field LAN

                            │
                            │
                     ┌──────▼───────┐
                     │ Kali Linux   │
                     │ Security     │
                     │ Workstation  │
                     └──────────────┘
```

This workstation is intended for authorized experimentation within the isolated laboratory, including network discovery, packet analysis, protocol testing, and defensive security exercises.

---

# Automated Topology Deployment

The entire GNS3 environment is created programmatically.

The deployment process is conceptually:

```text
Create Project
     │
     ▼
Create Nodes
     │
     ▼
Configure Interfaces
     │
     ▼
Refresh GNS3 Inventory
     │
     ▼
Create Links
     │
     ▼
Start Devices
     │
     ▼
Validate Environment
```

The topology builder is responsible for operations such as:

* Creating the project
* Creating PLCs
* Creating HMIs
* Creating SCADA infrastructure
* Creating field devices
* Creating network switches/segments
* Configuring Docker interfaces
* Creating device links
* Starting required nodes
* Performing connectivity validation

Jenkins can invoke the deployment process automatically.

This reduces configuration drift and makes it possible to reproduce the same laboratory topology consistently.

---

# Deployment Validation

Topology creation alone does not guarantee that the laboratory is operational.

The deployment workflow is intended to validate the environment progressively:

```text
Topology Created
      │
      ▼
Interfaces Present
      │
      ▼
Routes Valid
      │
      ▼
TCP Connectivity
      │
      ▼
Modbus TCP
      │
      ▼
PLC Metadata
      │
      ▼
SCADA Discovery
      │
      ▼
Application Health
```

This validation model allows deployment failures to be identified at the appropriate layer.

For example:

* A missing interface is a configuration problem.
* A failed ping may indicate routing or addressing.
* A failed TCP/502 connection may indicate a PLC service or network problem.
* A successful Modbus connection with invalid metadata indicates a protocol/application problem.
* Successful PLC communication with failed discovery indicates an SCADA discovery problem.

This layered validation approach is an important part of the project's design.

---

# Why Segmentation Matters

Segmentation allows the laboratory to demonstrate several important OT security and engineering concepts:

* Separation of field and supervisory networks
* PLC network boundaries
* Controlled SCADA communication
* Multi-interface industrial controllers
* Independent process segments
* Reduced broadcast domains
* Isolated failure domains
* Network troubleshooting by process area
* Controlled exposure of industrial protocols

The architecture also provides a foundation for future security controls such as firewalls, monitoring sensors, IDS/IPS systems, and network detection rules.

---

# Troubleshooting Strategy

The laboratory is designed to support troubleshooting from the lowest applicable layer upward.

## 1. Interface Configuration

Verify interface state and addressing:

```bash
ip addr
ip route
```

## 2. Network Connectivity

Verify that expected interfaces, routes, and paths exist.

## 3. TCP Connectivity

Verify that required services are reachable.

For Modbus TCP, the primary service is:

```text
TCP/502
```

## 4. Modbus Validation

Perform direct Modbus reads against the PLC.

This confirms that the industrial protocol is functioning independently of the SCADA application.

## 5. Metadata Validation

Verify the PLC metadata block and ensure it conforms to the expected protocol contract.

## 6. SCADA Discovery

Test the SCADA discovery client independently from the web dashboard.

## 7. Application Layer

Finally, validate the SCADA API and web interface.

The resulting troubleshooting model is:

```text
Interface
   ↓
Routing
   ↓
TCP
   ↓
Modbus
   ↓
Metadata
   ↓
Discovery
   ↓
SCADA Application
```

This approach prevents an application-layer failure from being incorrectly diagnosed as a network problem, and vice versa.

---

# Sanitized Addressing

The public repository intentionally does not document the actual addressing used by any private deployment environment.

Architecture documentation uses logical network identifiers such as:

```text
Process-A
Process-B
Process-C
Field-A
Field-B
Field-C
```

Rather than publishing deployment-specific addresses.

When examples require an IP address, documentation should use **documentation-only/example ranges** that are clearly unrelated to any private infrastructure.

Actual deployment addressing belongs in local configuration and should not be committed when it contains environment-specific information.

---

# Security Considerations

This project is designed for isolated educational and research environments.

The public repository should never contain:

* Credentials
* API keys or access tokens
* VPN configuration
* Private server information
* Internal infrastructure addresses
* Production network information
* Private Jenkins configuration
* Proprietary course materials
* Environment-specific secrets

Sensitive configuration should be provided through environment variables or local configuration files excluded from version control.

---

# Future Extensions

Potential extensions to the network architecture include:

* Industrial firewall zones
* OT DMZ architecture
* IDS/IPS monitoring
* Passive network sensors
* Modbus traffic analysis
* Protocol anomaly detection
* Network intrusion simulations
* Automated security validation
* PLC logic attack/defense scenarios
* Packet-capture-based investigations
* Additional process areas
* More realistic industrial control loops
* Blue-team detection and response exercises
