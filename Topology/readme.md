
# Topology

This directory contains the topology automation and architecture documentation for the Industrial Control Systems (ICS) / SCADA Sandbox.

The laboratory is designed to simulate a segmented wastewater treatment facility containing multiple process areas, PLCs, HMIs, field devices, and a centralized SCADA platform.

## Contents

### `480-build.py`

Python automation script used to build the GNS3 laboratory through the GNS3 API.

The builder is responsible for:

* Creating the GNS3 project
* Creating PLC, HMI, SCADA, sensor, and network-switch nodes
* Configuring Docker network interfaces
* Establishing process and SCADA network connections
* Creating field-device network segments
* Connecting PLCs to their corresponding field devices
* Connecting PLCs and HMIs to the SCADA/process networks

The goal is to make the topology reproducible rather than requiring the entire environment to be manually recreated in GNS3.

### `network-architecture.md`

Detailed documentation covering:

* Network segmentation
* PLC architecture
* HMI placement
* SCADA connectivity
* Field-device networks
* Modbus TCP communication
* Automated deployment
* Design decisions and troubleshooting considerations

### `topology-overview.md`

High-level architecture diagram describing the major components and communication paths within the laboratory.

## Architecture Summary

```text
                         Jenkins
                            |
                            v
                    GNS3 API / Builder
                            |
                            v
                     +-------------+
                     |    SCADA    |
                     +------+------+
                            |
           +----------------+----------------+
           |                |                |
         PLC              PLC              PLC ...
           |                |                |
        HMI +           HMI +           HMI +
        Field           Field           Field
       Devices         Devices         Devices
```

The complete environment contains seven simulated process areas:

| Process Area  | Primary Controller |
| ------------- | ------------------ |
| Influent      | PLC-Influent       |
| Primary       | PLC-Primary        |
| Aeration      | PLC-Aeration       |
| Clarification | PLC-Clarification  |
| Disinfection  | PLC-Disenfection   |
| Thickening    | PLC-Thickening     |
| Digestion     | PLC-Digestion      |

Each process area contains a PLC connected to a dedicated field-device network and an HMI/process network.

## Design Goals

The topology was designed around several principles:

**Segmentation**

Each process area has its own logical field network and process communication segment.

**Reproducibility**

The GNS3 environment can be rebuilt through automation instead of relying on manual configuration.

**Protocol realism**

PLC communications use Modbus TCP, while the PLCs expose structured metadata and aggregate process data.

**Layered troubleshooting**

The topology allows individual network, PLC, Modbus, SCADA, and application layers to be tested independently.

**Isolation**

The laboratory is intended to remain an isolated educational ICS environment rather than representing a production deployment.

## Deployment Flow

```text
Jenkins
   |
   v
Python Topology Builder
   |
   v
GNS3 API
   |
   +--> Create Nodes
   +--> Configure Interfaces
   +--> Create Links
   +--> Start Containers
   |
   v
Operational ICS / SCADA Sandbox
```

## Public Repository Notes

The public repository is intentionally sanitized.

Real infrastructure addresses, credentials, university-specific configuration, and other environment-specific information should not be committed to source control.
