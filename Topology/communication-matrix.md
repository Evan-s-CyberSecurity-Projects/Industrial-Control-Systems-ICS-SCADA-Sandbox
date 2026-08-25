| Source  | Destination  |   Protocol | Port | Purpose                     |
| ------- | ------------ | ---------: | ---: | --------------------------- |
| SCADA   | PLC          | Modbus TCP |  502 | Process data                |
| HMI     | PLC          | Modbus TCP |  502 | Process interaction         |
| PLC     | Field Device |  Simulated |    — | Sensor/actuator data        |
| Kali    | PLC          |        TCP |  502 | Authorized security testing |
| Jenkins | GNS3         |   HTTP/API |    — | Deployment                  |
