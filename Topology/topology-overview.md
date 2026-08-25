Internet / Host
      │
      ▼
  GNS3 Project
      │
 ┌────┴─────────────────────┐
 │                          │
Security Workstation      OT Network
 │                          │
Kali                    ┌───┴────────────┐
                        │                │
                      SCADA            Process
                                         │
                           ┌─────────────┼─────────────┐
                           ▼             ▼             ▼
                          PLC           PLC           PLC
                           │             │             │
                        Field LAN     Field LAN     Field LAN
