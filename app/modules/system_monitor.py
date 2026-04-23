"""
System Monitoring Module
Monitors CPU, RAM, and general system resources
"""

import psutil
import os
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class CPUInfo:
    percent: float
    cores: int
    freq: float
    load_avg: Tuple[float, float, float]

@dataclass
class MemoryInfo:
    total: int
    available: int
    used: int
    percent: float

@dataclass
class DiskInfo:
    mountpoint: str
    total: int
    used: int
    free: int
    percent: float

@dataclass
class NetworkInfo:
    interface: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int

class SystemMonitor:
    """Monitor system resources"""

    def __init__(self):
        self.boot_time = psutil.boot_time()
        self.prev_net_io = None

    def get_cpu_info(self) -> CPUInfo:
        """Get CPU information"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cores = psutil.cpu_count()
        freq = psutil.cpu_freq()
        try:
            load_avg = os.getloadavg()
        except (AttributeError, OSError):
            load_avg = (0.0, 0.0, 0.0)

        return CPUInfo(
            percent=cpu_percent,
            cores=cores,
            freq=freq.current if freq else 0,
            load_avg=load_avg
        )

    def get_memory_info(self) -> MemoryInfo:
        """Get memory information"""
        mem = psutil.virtual_memory()
        return MemoryInfo(
            total=mem.total,
            available=mem.available,
            used=mem.used,
            percent=mem.percent
        )

    def get_swap_info(self) -> MemoryInfo:
        """Get swap memory information"""
        swap = psutil.swap_memory()
        return MemoryInfo(
            total=swap.total,
            available=swap.total - swap.used,
            used=swap.used,
            percent=swap.percent
        )

    def get_disk_info(self) -> List[DiskInfo]:
        """Get disk information"""
        disks = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append(DiskInfo(
                    mountpoint=partition.mountpoint,
                    total=usage.total,
                    used=usage.used,
                    free=usage.free,
                    percent=usage.percent
                ))
            except PermissionError:
                continue
            except Exception:
                continue
        return disks

    def get_network_info(self) -> List[NetworkInfo]:
        """Get network I/O information"""
        net_io = psutil.net_io_counters(pernic=True)
        interfaces = []
        for interface, data in net_io.items():
            interfaces.append(NetworkInfo(
                interface=interface,
                bytes_sent=data.bytes_sent,
                bytes_recv=data.bytes_recv,
                packets_sent=data.packets_sent,
                packets_recv=data.packets_recv
            ))
        return interfaces

    def get_uptime(self) -> str:
        """Get system uptime"""
        import time
        uptime_seconds = time.time() - self.boot_time
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"

    def get_system_summary(self) -> Dict:
        """Get complete system summary"""
        cpu = self.get_cpu_info()
        mem = self.get_memory_info()
        swap = self.get_swap_info()
        disks = self.get_disk_info()

        return {
            "cpu": cpu,
            "memory": mem,
            "swap": swap,
            "disks": disks,
            "uptime": self.get_uptime(),
            "hostname": os.uname().nodename
        }

    @staticmethod
    def format_bytes(bytes_value: int) -> str:
        """Format bytes to human readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"

    @staticmethod
    def format_percent(value: float) -> str:
        """Format percentage with color indicator"""
        if value >= 90:
            return f"{value:.1f}% [CRITICAL]"
        elif value >= 70:
            return f"{value:.1f}% [WARNING]"
        else:
            return f"{value:.1f}%"
