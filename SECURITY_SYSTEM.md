# CRM Security Guidelines & Recommendations

This document outlines the security posture, recommendations, and best practices for the CRM server running on the local network (`http://192.168.1.20:8000`) for a small office setup (2-3 team members on the same Wi-Fi).

---

## 1. Current Security Posture

* **Server Binding:** Uvicorn is bound to `0.0.0.0:8000`, allowing devices on the local network to connect.
* **Network Scope:** The server is restricted to the local network (LAN) and is not accessible from the public Internet (unless port forwarding is enabled on your router).
* **Traffic Encryption:** Operating over standard unencrypted `HTTP`.
* **Access Control:** Anyone on the local Wi-Fi network who visits `http://192.168.1.20:8000` currently has access to the CRM interface and database.

---

## 2. Recommended Security Enhancements for Small Office Setup

### 1. Reserve a Static IP Address for the Host PC (High Priority)
* **Purpose:** Prevents router IP reassignments from breaking team access.
* **Action:** Set a DHCP reservation in your Wi-Fi router for your PC's MAC address, or set your Windows IPv4 settings to static `192.168.1.20`.

### 2. Add User Authentication / Login (High Priority)
* **Purpose:** Prevents unauthorized devices or visitors on the Wi-Fi from viewing or modifying CRM data.
* **Action:** Implement a login screen or HTTP Basic Auth / Passcode protection with individual user accounts for team members.

### 3. Restrict Windows Firewall Inbound Access (Medium Priority)
* **Purpose:** Restricts access strictly to known team member devices.
* **Action:** Configure the Windows Firewall rule on port 8000 to only allow connections from specific team member local IP addresses (e.g., `192.168.1.21`, `192.168.1.22`).

### 4. Enable Local HTTPS (Medium Priority)
* **Purpose:** Encrypts network traffic over Wi-Fi so passwords and CRM data cannot be intercepted locally.
* **Action:** Generate a local SSL certificate using `mkcert` and configure Uvicorn with `ssl_keyfile` and `ssl_certfile` in `run.py`.

### 5. Automated Daily Database Backups (High Priority)
* **Purpose:** Protects CRM data (`crm.db`) against corruption, hardware failure, or accidental deletion.
* **Action:** Schedule a daily task or script to back up `crm.db` to a secure backup directory or cloud storage.

---

## 3. Best Practices for Wi-Fi & Office Environment

* **Secure Wi-Fi:** Ensure office Wi-Fi uses strong WPA2/WPA3 encryption with a robust password.
* **Guest Networks:** Keep visitors or personal devices on a separate Guest Wi-Fi network isolated from the main office LAN.
* **Public Wi-Fi Precaution:** If taking the host laptop offsite to a public Wi-Fi network (coffee shop, hotel), ensure Windows network location is set to **Public** to block incoming connections on port 8000.
