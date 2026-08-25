# Jenkins Deployment

This directory contains the Jenkins pipeline used to automate deployment of the ICS/SCADA Sandbox.

The pipeline:

1. Retrieves the deployment source
2. Installs required dependencies
3. Executes the GNS3 topology deployment
4. Reports deployment success or failure

The goal is to make the laboratory reproducible and reduce manual GNS3 configuration.

## Pipeline Flow

```text
Jenkins
   ↓
Source Repository
   ↓
Deployment Environment
   ↓
Python / GNS3 API
   ↓
ICS/SCADA Topology
   ↓
Deployment Result
