# Topology Overview

The ICS/SCADA Sandbox is a virtualized industrial control environment designed to simulate a small wastewater treatment facility.

The topology contains a centralized SCADA system, seven process PLCs, seven HMIs, simulated field devices, and a dedicated security workstation. The environment is deployed programmatically through the GNS3 API rather than being manually assembled.

## High-Level Topology

```text
                         ┌──────────────────────┐
                         │       Jenkins        │
                         │  Deployment Pipeline │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Python / GNS3 API  │
                         │   Topology Builder   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │        SCADA         │
                         │ Dashboard / Discovery│
                         └──────────┬───────────┘
                                    │
                         SCADA / Control Network
                                    │
          ┌───────────┬─────────────┼─────────────┬───────────┐
          │           │             │             │           │
          ▼           ▼             ▼             ▼           ▼
        PLC-1       PLC-2         PLC-3         PLC-4       PLC...
          │           │             │             │
         HMI         HMI           HMI           HMI
          │           │             │             │
       Field       Field         Field         Field
      Devices     Devices       Devices       Devices

                                    │
                                    ▼
                           Kali Linux Workstation
```

## Process Areas

The simulated facility is divided into seven process areas:

| Process Area  | Controller        |
| ------------- | ----------------- |
| Influent      | PLC-Influent      |
| Primary       | PLC-Primary       |
| Aeration      | PLC-Aeration      |
| Clarification | PLC-Clarification |
| Disinfection  | PLC-Disinfection  |
| Thickening    | PLC-Thickening    |
| Digestion     | PLC-Digestion     |

Each process area contains:

* A dedicated PLC
* An HMI
* Simulated sensors and actuators
* A local field-device network
* A connection to the higher-level process/SCADA network

## Communication Model

The topology uses a layered communication model:

```text
Field Devices
      │
      ▼
     PLC
      │
      ├──────────► HMI
      │
      └──────────► SCADA
```

Field devices communicate with their local PLC.

The PLC exposes process data and device metadata to higher-level systems. SCADA communicates with the PLCs using **Modbus TCP**, allowing the SCADA system to discover PLCs and retrieve their process data.

## Network Segmentation

The topology separates local field-device traffic from higher-level process communications.

```text
        Field Network
             │
     ┌───────▼───────┐
     │      PLC      │
     └───────┬───────┘
             │
        Process Network
             │
        ┌────┴────┐
        ▼         ▼
       HMI      SCADA
```

Each process area has its own logical field segment. This provides process isolation and creates distinct network boundaries for troubleshooting and security testing.

Specific deployment addresses are intentionally excluded from the public documentation.

## Automation

The topology is generated through a Python deployment system using the **GNS3 API**.

The deployment process creates and configures the virtual infrastructure, including:

* GNS3 project
* Network segments and switches
* PLCs
* HMIs
* SCADA
* Field devices
* Network interfaces
* Device links

Jenkins can invoke the deployment process to provide a repeatable build workflow.

## Validation

A successful deployment is more than simply creating the GNS3 nodes.

The environment is validated progressively:

```text
Topology
   ↓
Interfaces
   ↓
Network Connectivity
   ↓
Modbus TCP
   ↓
PLC Metadata
   ↓
SCADA Discovery
   ↓
Operational SCADA
```

The completed laboratory successfully demonstrates SCADA communication and automatic discovery of **seven simulated PLCs**.

## Security Testing

A Kali Linux workstation can be connected to the isolated OT environment for authorized security research and testing.

This provides a controlled environment for studying:

* Network reconnaissance
* Industrial protocol traffic
* Modbus TCP
* SCADA asset discovery
* Packet analysis
* Defensive monitoring

The environment is isolated and intended for educational and authorized testing only.

## Related Documentation

* [`README.md`](./README.md) — topology directory overview
* [`network-architecture.md`](./network-architecture.md) — detailed architecture and communication design
* [`../deployment/`](../deployment/) — automated topology deployment
