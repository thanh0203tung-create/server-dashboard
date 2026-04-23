"""
Configuration for Server Dashboard
"""

import os

class Config:
    # Refresh intervals (seconds)
    REFRESH_INTERVAL_SYSTEM = 2
    REFRESH_INTERVAL_SERVICES = 5
    REFRESH_INTERVAL_DOCKER = 5
    REFRESH_INTERVAL_K8S = 5
    REFRESH_INTERVAL_PROCESSES = 3
    REFRESH_INTERVAL_LOGS = 0  # Manual refresh

    # Log settings
    MAX_LOG_LINES = 1000
    DEFAULT_LOG_PATH = "/var/log/syslog"
    JOURNALCTL_LINES = 100

    # Process filter
    PROCESS_IGNORE_LIST = ['init', 'kthreadd', 'migration', 'watchdog', 'ksoftirqd', 'rcu_']
    MIN_CPU_PERCENT = 0.1
    MIN_MEM_PERCENT = 0.1

    # UI Settings
    MAX_ROWS_DISPLAY = 50
    COLOR_SCHEME = "dark"

    # Kubernetes
    K8S_NAMESPACE = "default"
    K8S_CONTEXT = None  # Use current context

    # Docker
    DOCKER_SOCKET = "unix:///var/run/docker.sock"
