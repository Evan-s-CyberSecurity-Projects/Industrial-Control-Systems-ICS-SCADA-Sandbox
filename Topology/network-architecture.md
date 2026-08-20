
# Network Architecture

## Overview

The ICS/SCADA Sandbox models a wastewater treatment facility using a segmented industrial network architecture.

The environment separates field-device communications from PLC-to-SCADA communications while providing each process area with its own logical network.

The architecture contains seven process areas:

1. Influent
2. Primary
3. Aeration
4. Clarification
5. Disinfection
6. Thickening
7. Digestion

Each area contains:

* A process PLC
* An HMI
* Multiple sensors and/or actuators
* A dedicated field-device network
* A dedicated PLC/HMI/SCADA process network

A centralized SCADA server communicates with the PLCs using Modbus TCP.

---

## High-Level Architecture

```text
                         +----------------------+
                         |       Jenkins        |
                         |  Automated Deployment |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |    GNS3 API /        |
                         |    Topology Builder   |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |    SCADA Server       |
                         | Flask / Historian     |
                         +----------+-----------+
                                    |
             +----------------------+----------------------+
             |          |            |           |          |
             v          v            v           v          v
           PLC        PLC          PLC         PLC        PLC ...
             |          |            |           |          |
            HMI        HMI          HMI         HMI       HMI
             |          |            |           |          |
         Field LAN   Field LAN   Field LAN   Field LAN   Field LAN
```

---

## Process Area Segmentation

Each process area has a separate logical field network.

The exact addresses used by the private laboratory are intentionally omitted from public documentation.

A sanitized representation is:

| Process Area  | Process Network | Field Network | PLC               |
| ------------- | --------------- | ------------- | ----------------- |
| Influent      | Process-A       | Field-A       | PLC-Influent      |
| Primary       | Process-B       | Field-B       | PLC-Primary       |
| Aeration      | Process-C       | Field-C       | PLC-Aeration      |
| Clarification | Process-D       | Field-D       | PLC-Clarification |
| Disinfection  | Process-E       | Field-E       | PLC-Disenfection  |
| Thickening    | Process-F       | Field-F       | PLC-Thickening    |
| Digestion     | Process-G       | Field-G       | PLC-Digestion     |

Each PLC effectively acts as the boundary between its local field network and the higher-level SCADA/process network.

---

## PLC Architecture

A typical PLC uses two logical interfaces:

```text
                     PLC
              +----------------+
 Field LAN <--| Field Interface |
              |                |
 Process LAN <-| SCADA Interface |
              +----------------+
```

The field-facing interface communicates with local sensors and actuators.

The process-facing interface communicates with:

* SCADA
* HMI infrastructure
* Other authorized process-network services

This architecture demonstrates the concept of a PLC bridging different logical segments of an OT environment.

---

## Field Devices

Field devices are simulated as lightweight Docker nodes.

Examples include:

### Influent

* FT-101 — Flow
* LT-101 — Level
* DP-101 — Differential Pressure
* P-101 — Pump

### Primary

* FT-201 — Flow
* LT-201 — Level
* DP-201 — Differential Pressure
* MV-201 — Mixer

### Aeration

* DO-301 — Dissolved Oxygen
* FT-301 — Flow
* MLSS-301 — Mixed Liquor Suspended Solids
* SV-301 — Blower

### Clarification

* FT-401 — Flow
* LT-401 — Level
* TU-401 — Turbidity
* DL-401 — Dosing

### Disinfection

* CL-501 — Chlorine
* FT-501 — Flow
* LT-501 — Level
* AV-501 — Valve

### Thickening

* LT-601 — Level
* FT-601 — Sludge Flow
* SS-601 — Solids
* P-601 — Pump

### Digestion

* T-701 — Temperature
* PT-701 — Pressure
* FT-701 — Flow
* GAS-701 — Gas Flow

---

## PLC-to-SCADA Communication

SCADA communicates with the PLCs using Modbus TCP.

The standard communication path is:

```text
SCADA
  |
  | Modbus TCP / TCP 502
  |
  v
PLC
  |
  +--> Metadata block
  |
  +--> Aggregate sensor table
  |
  +--> Current process values
```

The SCADA client first identifies a PLC through its metadata block.

After a PLC is discovered, SCADA reads the PLC's aggregate child-device table rather than requiring direct SCADA access to every field device.

This creates a layered architecture:

```text
SCADA
  |
  v
PLC
  |
  +--> Sensor 1
  +--> Sensor 2
  +--> Sensor 3
  +--> Actuator
  +--> ...
```

---

## Metadata Architecture

The simulated PLCs expose a structured metadata block containing information such as:

* Protocol version
* Device kind
* Device class
* Device tag
* Units
* Data type
* Data register count
* Data register starting address
* Polling hint
* Writable state
* Description

This allows the SCADA client to discover devices without requiring a hardcoded definition for every individual device.

The discovery process is conceptually:

```text
Connect to PLC
      |
      v
Read metadata
      |
      v
Validate protocol
      |
      v
Identify PLC
      |
      v
Read aggregate table
      |
      v
Create virtual sensor states
      |
      v
Poll process values
```

---

## HMI Architecture

Each process area also contains an HMI node.

The HMI provides a process-facing interface for interacting with the simulated process environment.

The architecture separates the roles of:

```text
Field Devices
      |
      v
     PLC
      |
      +------------+
      |            |
      v            v
     HMI          SCADA
```

The HMI is therefore not required for SCADA PLC discovery.

This distinction became useful during troubleshooting because an individual HMI console problem could be isolated without implying a failure of the underlying PLC/SCADA communication path.

---

## Automated Topology Deployment

The entire GNS3 environment is created programmatically.

The builder performs operations such as:

```text
Create Project
     |
     v
Create Nodes
     |
     v
Configure Docker Interfaces
     |
     v
Refresh GNS3 Inventory
     |
     v
Create Network Links
     |
     v
Start / Verify Devices
```

Jenkins can invoke the builder to produce a repeatable laboratory environment.

This reduces configuration drift and makes it easier to recreate the lab after changes.

---

## Why Segmentation Matters

Segmentation allows the laboratory to model several important OT security concepts:

* Separation of field and process networks
* PLC network boundaries
* Restriction of direct field-device access
* Controlled SCADA communication
* Multi-interface industrial controllers
* Independent failure domains
* Network troubleshooting by process area

It also provides a realistic environment for future defensive-security experiments.

---

## Troubleshooting Strategy

The architecture supports troubleshooting from the lowest layer upward.

### Layer 1 — Interface Configuration

Verify:

```bash
ip addr
ip route
```

### Layer 2/3 — Connectivity

Verify that the appropriate network interfaces and routes exist.

### Layer 4 — TCP

Verify that PLC Modbus services are listening on TCP port 502.

### Layer 7 — Modbus

Perform direct register reads against a PLC.

### Application Layer

Test SCADA discovery and the SCADA API independently.

This layered approach makes it possible to distinguish a topology problem from a PLC problem, a protocol problem, or an application problem.

---

## Sanitized Addressing

The public repository intentionally avoids publishing the actual laboratory addressing scheme.

Documentation examples should use generic ranges such as:

```text
Process network:
10.10.x.0/24

Field network:
10.20.x.0/24

SCADA:
10.10.x.200

PLC:
10.10.x.5
10.20.x.5
```

Actual deployment values should remain environment-specific.

---

## Security Considerations

This topology is intended for an isolated educational environment.

The public repository should not contain:

* Credentials
* API tokens
* Internal hostnames
* University infrastructure addresses
* VPN configuration
* Production network information
* Proprietary course materials
* Private Jenkins configuration

Sensitive values should instead be provided through environment variables or local configuration files excluded from Git.

---

## Future Extensions

Potential additions include:

* Industrial IDS monitoring
* Modbus traffic analysis
* Protocol anomaly detection
* Network intrusion simulations
* Firewalling between process zones
* Automated security validation
* PLC logic attack/defense scenarios
* Packet-capture-based investigations
* Additional simulated process areas
* More realistic control loops
