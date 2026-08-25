# Deployment

This directory contains the automation used to build and configure the ICS/SCADA Sandbox in GNS3.

The deployment system uses **Python and the GNS3 API** to create the laboratory programmatically, configure network interfaces, establish device connections, and start the required infrastructure.

The purpose of the deployment system is to make the environment **repeatable and consistent** rather than requiring the entire ICS topology to be manually recreated.

---

## Deployment Workflow

```text
                     Python Deployment
                            │
                            ▼
                        GNS3 API
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
        Create Nodes   Configure       Create Links
                       Interfaces
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                       Start Devices
                            │
                            ▼
                     Validate Network
                            │
                            ▼
                    Validate Modbus
                            │
                            ▼
                     SCADA Discovery
                            │
                            ▼
                    Operational Lab
```

---

## What the Deployment System Creates

The automation is responsible for creating and configuring the major components of the laboratory:

* SCADA server
* Process PLCs
* HMIs
* Field sensors and actuators
* Network switches and segments
* Security workstation
* Network interfaces
* Device-to-device links

The deployment also applies the required network configuration to the virtual devices.

---

## Deployment Validation

The deployment process is intended to validate the resulting environment rather than stopping after GNS3 reports that the project was created.

Validation follows the system from the network layer upward:

```text
GNS3 Topology
      ↓
Network Interfaces
      ↓
Connectivity
      ↓
TCP Services
      ↓
Modbus TCP
      ↓
PLC Metadata
      ↓
SCADA Discovery
      ↓
Application Availability
```

This allows infrastructure failures, network failures, PLC communication failures, and SCADA application failures to be distinguished from one another.

A successful deployment should result in the SCADA system communicating with and discovering the expected simulated PLCs.

---

## Running the Deployment

The deployment requires access to a GNS3 server with the required templates and images configured.

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

Configure the GNS3 connection using the deployment environment variables or local configuration required by the script.

Then run:

```bash
python deploy.py
```

The script should report the major deployment stages and return a non-zero exit status when a required validation step fails.

---

## Requirements

The deployment system uses:

* Python 3
* GNS3
* GNS3 API
* `gns3fy`
* Docker-based GNS3 nodes
* The ICS/SCADA container images used by the laboratory

The exact Python dependencies are listed in [`requirements.txt`](./requirements.txt).

---

## Design Goals

### Reproducibility

The same deployment logic can be used to recreate the laboratory without manually rebuilding the topology.

### Automation

Node creation, interface configuration, and network connections are handled programmatically.

### Validation

The deployment process should verify that the resulting environment is actually functional rather than reporting success based solely on topology creation.

### Failure Visibility

Deployment failures should be explicit so that problems can be identified and corrected instead of being silently ignored.

---

## Public Repository Configuration

The public repository does not contain private infrastructure configuration.

The deployment code should not contain:

* Credentials
* API tokens
* Private server addresses
* Internal hostnames
* VPN configuration
* Environment-specific secrets

These values should be supplied through environment variables or local configuration excluded from version control.

---

## Related Documentation

* [`../Topology/`](../Topology/) — network architecture and topology documentation
* [`../SCADA/`](../SCADA/) — SCADA implementation
* [`../Jenkins/`](../Jenkins/) — automated CI/CD deployment
