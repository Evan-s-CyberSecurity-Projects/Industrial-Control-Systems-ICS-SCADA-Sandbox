# SCADA & ICS Network Security Lab

## Project Overview
I built this isolated Industrial Control Systems (ICS) and SCADA sandbox using GNS3. My main goal was to simulate an operational technology (OT) network, learn how to analyze industrial traffic, and get hands-on experience troubleshooting complex network routing issues in a safe environment.

## What I Learned & Troubleshooting Steps
* **Fixing a Layer 3 Routing Conflict:** During the build, I ran into a major network issue where two container interfaces (`eth6` and `eth7`) were accidentally assigned to the exact same subnet (`172.25.70.0/24`). This caused asymmetrical routing—my nmap scans were returning a `filtered` state because the server was trying to reply out of the wrong interface.
* **Network Segregation:** To fix the dropped packets, I redesigned the topology. I created a dedicated out-of-band management network (`172.25.99.0/24`) to separate the web dashboard traffic from the backend PLC network.
* **Linux Container Networking:** The Docker containers in this lab were minimal and didn't have firewalls like `iptables` or `ufw` installed. I had to learn how to manually check listening ports and flush routing tables directly using Linux kernel commands like `ip route`, `ip addr`, and `ss`.
* **Traffic Sniffing:** I used Wireshark to capture the live traffic between my Kali machine and the SCADA server to analyze how the API transmits data. 

## Network Architecture
This lab maps a security auditing machine to an isolated SCADA web server. 

* **Security Testing Node (Kali Linux):** `172.25.99.250` 
* **SCADA Web Dashboard (eth7):** `172.25.99.201:8080` 
* **Production ICS Network (eth6):** `172.25.70.201` (Reserved for Digester PLCs)
