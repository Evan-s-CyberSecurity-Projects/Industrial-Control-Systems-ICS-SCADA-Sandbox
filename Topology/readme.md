# Topology

This directory contains the network architecture documentation and topology-related resources for the **Industrial Control Systems (ICS) / SCADA Sandbox**.

The laboratory models a segmented wastewater treatment facility containing multiple process areas, simulated PLCs, HMIs, field devices, and a centralized SCADA platform.

The topology is designed to be **reproducible, segmented, and independently testable**, with automated deployment handled through the GNS3 API.

---

## Contents

### `network-architecture.md`

Detailed documentation of the laboratory's network design and communication model.

Topics include:

* OT network segmentation
* Process-area isolation
* PLC architecture
* HMI placement
* SCADA communications
* Field-device networks
* Modbus TCP
* PLC metadata and device discovery
* Automated topology deployment
* Network and application troubleshooting

### `topology-overview.md`

High-level overview of the major components in the laboratory and the communication paths between them.

This document provides a simplified view of the environment before moving into the detailed network architecture.

---

## Topology Automation

The actual topology deployment logic is maintained in the project's [`deployment/`](../deployment/) directory.

The deployment system uses Python and the **GNS3 API** to build the virtual laboratory programmatically rather than requiring every node and connection to be configured manually.

The builder is responsible for tasks such as:

* Creating the GNS3 project
* Creating PLC nodes
* Creating HMI nodes
* Creating the SCADA server
* Creating sensors and actuators
* Creating network switches and segments
* Configuring Docker network interfaces
* Creating device-to-device links
* Starting required nodes
* Performing deployment validation

This separation keeps **topology documentation** separate from **deployment automation**.

---

## Architecture Summary

```text
                         Jenkins
                            │
                            ▼
                    Python Deployment
                            │
                            ▼
                         GNS3 API
                            │
                            ▼
                    Virtual OT Network
                            │
                 ┌──────────┼──────────┐
                 │          │          │
                PLC        PLC        PLC ...
                 │          │          │
              ┌──┴──┐    ┌──┴──┐    ┌──┴──┐
              │ HMI │    │ HMI │    │ HMI │
              └─────┘    └─────┘    └─────┘
                 │          │          │
              Field      Field      Field
             Devices    Devices    Devices
                 │          │          │
                 └──────────┼──────────┘
                            │
                          SCADA
```

The laboratory contains seven simulated process areas:

| Process Area  | Primary Controller |
| ------------- | ------------------ |
| Influent      | PLC-Influent       |
| Primary       | PLC-Primary        |
| Aeration      | PLC-Aeration       |
| Clarification | PLC-Clarification  |
| Disinfection  | PLC-Disinfection   |
| Thickening    | PLC-Thickening     |
| Digestion     | PLC-Digestion      |

Each process area contains a PLC connected to its local field-device network and an HMI/process network.

---

## Network Model

Each process area contains two primary logical communication domains:

```text
                  ┌──────────────────┐
                  │       PLC        │
                  └───────┬───┬──────┘
                          │   │
                 Field    │   │    Process
                 Network  │   │    Network
                          │   │
                          ▼   ▼
                      Sensors  SCADA
                      /       HMI
                   Actuators
```

The field network contains the sensors and actuators associated with the process.

The process network provides communication between the PLC and higher-level systems such as SCADA and HMI infrastructure.

This architecture allows the project to demonstrate the concept of a PLC acting as a boundary between local process devices and supervisory systems.

---

## Design Goals

The topology was designed around several core engineering principles.

### Segmentation

Each process area has its own logical field network, reducing unnecessary communication between unrelated process devices.

### Reproducibility

The environment can be generated programmatically rather than relying on a manually constructed GNS3 project.

### Protocol Realism

PLC communications use **Modbus TCP**, while simulated PLCs expose structured metadata and aggregate process data to higher-level systems.

### Layered Troubleshooting

Network interfaces, routing, TCP connectivity, Modbus communication, PLC metadata, SCADA discovery, and application services can be tested independently.

### Isolation

The environment is designed as an isolated laboratory for authorized cybersecurity experimentation and does not represent a production ICS deployment.

---

## Deployment Flow

```text
                     Jenkins
                        │
                        ▼
                Python Deployment
                        │
                        ▼
                     GNS3 API
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
      Create Nodes  Configure      Create Links
                     Interfaces
          │             │             │
          └─────────────┼─────────────┘
                        ▼
                  Start Devices
                        │
                        ▼
               Validate Environment
                        │
                        ▼
              Operational ICS Lab
```

The deployment process is intended to validate more than simple node creation.

A successful deployment should ultimately provide an operational path from the SCADA layer through the PLCs to the simulated field devices.

---

## Troubleshooting Model

The topology supports a layered troubleshooting workflow:

```text
GNS3 Topology
      ↓
Interface Configuration
      ↓
Routing / Connectivity
      ↓
TCP Services
      ↓
Modbus TCP
      ↓
PLC Metadata
      ↓
SCADA Discovery
      ↓
SCADA Application
```

This makes it possible to identify whether a failure originates from:

* The virtual topology
* Network configuration
* Routing
* A PLC service
* Modbus communications
* Metadata validation
* SCADA device discovery
* The SCADA application itself

This layered approach was an important part of the project's development and continues to guide the design of the deployment system.

---

## Public Repository Notes

The public repository is intentionally sanitized for portfolio use.

The repository should not contain:

* Real credentials
* API keys or tokens
* Private infrastructure addresses
* VPN configuration
* Internal server information
* University-specific infrastructure
* Proprietary course materials
* Environment-specific secrets

Deployment-specific values should be supplied through local configuration or environment variables and excluded from version control when necessary.

The diagrams and documentation in this directory describe the **architecture and behavior of the laboratory**, not any private production infrastructure.

---

## Related Documentation

* [`../deployment/`](../deployment/) — automated GNS3 deployment
* [`network-architecture.md`](./network-architecture.md) — detailed network design
* [`topology-overview.md`](./topology-overview.md) — simplified topology overview
