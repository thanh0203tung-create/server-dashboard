# Server Dashboard - Terminal UI for Ubuntu Server Management

A beautiful and powerful TUI (Terminal User Interface) application for monitoring and managing Ubuntu servers. Built with Python and urwid.

## Features

### System Monitoring
- Real-time CPU usage monitoring
- Memory (RAM) and Swap usage
- Disk space information
- System uptime
- Load average

### Process Management
- List all running processes
- Sort by CPU or memory usage
- Kill processes (graceful or force)
- Search processes by name

### Systemd Services
- List all systemd services
- Filter by state (running/stopped/failed)
- Start, stop, restart services
- View service status and logs
- Enable/disable services for boot

### Docker Management
- List all containers (running and stopped)
- Container resource usage (CPU/Memory)
- Start, stop, restart containers
- Pause and unpause containers
- View container logs
- List images and volumes
- Docker system info

### Kubernetes Management
- List pods in namespace
- View pod status and restarts
- Container information
- View pod logs
- Scale deployments
- Delete pods
- Cluster information

### Log Viewer
- System logs (journalctl)
- Kernel logs (dmesg)
- Service-specific logs
- Search and filter logs
- Color-coded log levels

## Requirements

- Python 3.8+
- Ubuntu Linux (or any systemd-based Linux)
- Optional: Docker, Kubernetes cluster

## Installation

```bash
# Clone or copy the project
cd server-dashboard

# Install dependencies
pip install -r requirements.txt
```

### Optional Dependencies

For Docker support:
```bash
pip install docker>=6.1.3
```

For Kubernetes support:
```bash
pip install kubernetes>=28.1.0
```

## Usage

Run the dashboard:

```bash
python main.py
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` or `Ctrl+C` | Quit application |
| `r` | Refresh current screen |
| `s` | System overview |
| `p` | Process list |
| `v` | Services (systemd) |
| `d` | Docker containers |
| `K` | Kubernetes |
| `l` | Log viewer |
| `h` or `?` | Help |
| `1-7` | Jump to screen |
| `k` | Kill process |
| `Enter` | Execute action |

## Screenshots

The dashboard features a clean, terminal-based interface with:

- Header showing CPU, RAM, and uptime
- Left sidebar menu for navigation
- Main content area with detailed information
- Color-coded status indicators
- Footer with keyboard shortcuts

## Project Structure

```
server-dashboard/
├── main.py                 # Entry point
├── config.py               # Configuration
├── requirements.txt         # Python dependencies
├── app/
│   ├── __init__.py
│   ├── modules/
│   │   ├── system_monitor.py    # CPU, RAM, disk monitoring
│   │   ├── process_monitor.py   # Process listing and management
│   │   ├── service_manager.py   # Systemd services
│   │   ├── docker_manager.py    # Docker containers
│   │   ├── k8s_manager.py       # Kubernetes
│   │   └── log_viewer.py        # Log viewing
│   └── ui/
│       ├── __init__.py
│       ├── colors.py            # Color definitions
│       └── dashboard.py         # Main UI
└── README.md
```

## Color Legend

- **Green**: Good/Low usage, Running
- **Yellow**: Warning/Medium usage
- **Red**: Critical/High usage, Failed
- **Gray**: Stopped, Inactive

## Troubleshooting

### Permission Denied
Some operations require root privileges. Run with:
```bash
sudo python main.py
```

### Docker Not Found
Ensure Docker is installed and running:
```bash
docker --version
sudo systemctl status docker
```

### Kubernetes Not Configured
Ensure kubectl is configured:
```bash
kubectl cluster-info
```

## License

MIT License
