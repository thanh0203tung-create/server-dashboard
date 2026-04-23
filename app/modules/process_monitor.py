"""
Process Monitor Module
Monitors and manages running processes
"""

import psutil
import os
import signal
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class ProcessInfo:
    pid: int
    name: str
    username: str
    status: str
    cpu_percent: float
    memory_percent: float
    memory_rss: int
    num_threads: int
    create_time: float
    cmdline: List[str]

class ProcessMonitor:
    """Monitor and manage system processes"""

    def __init__(self):
        self.process_ignore_list = [
            'init', 'kthreadd', 'migration', 'watchdog', 'ksoftirqd',
            'rcu_', 'kworker', 'systemd', '(kswapd)', '(ksmd)', '(khugepaged)'
        ]

    def get_all_processes(self, min_cpu: float = 0.1, min_mem: float = 0.1) -> List[ProcessInfo]:
        """Get all running processes with optional filtering"""
        processes = []

        for proc in psutil.process_iter(['pid', 'name', 'username', 'status',
                                         'cpu_percent', 'memory_percent', 'memory_info',
                                         'num_threads', 'create_time', 'cmdline']):
            try:
                info = proc.info

                # Filter out kernel threads and system processes
                name = info.get('name', '')

                # Skip if in ignore list
                skip = False
                for ignore in self.process_ignore_list:
                    if name.startswith(ignore) or ignore in name:
                        skip = True
                        break

                if skip and info.get('username', '') == 'root':
                    continue

                cpu = info.get('cpu_percent', 0) or 0
                mem = info.get('memory_percent', 0) or 0

                # Apply filters
                if cpu < min_cpu and mem < min_mem:
                    continue

                mem_info = info.get('memory_info')
                rss = mem_info.rss if mem_info else 0

                processes.append(ProcessInfo(
                    pid=info['pid'],
                    name=name,
                    username=info.get('username', 'unknown'),
                    status=info.get('status', 'unknown'),
                    cpu_percent=cpu,
                    memory_percent=mem,
                    memory_rss=rss,
                    num_threads=info.get('num_threads', 1),
                    create_time=info.get('create_time', 0),
                    cmdline=info.get('cmdline', [])
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort by CPU usage
        processes.sort(key=lambda x: x.cpu_percent, reverse=True)
        return processes

    def get_top_cpu_processes(self, limit: int = 10) -> List[ProcessInfo]:
        """Get top processes by CPU usage"""
        all_procs = self.get_all_processes(min_cpu=0, min_mem=0)
        return all_procs[:limit]

    def get_top_memory_processes(self, limit: int = 10) -> List[ProcessInfo]:
        """Get top processes by memory usage"""
        all_procs = self.get_all_processes(min_cpu=0, min_mem=0)
        return sorted(all_procs, key=lambda x: x.memory_percent, reverse=True)[:limit]

    def get_process_by_pid(self, pid: int) -> Optional[ProcessInfo]:
        """Get specific process by PID"""
        try:
            proc = psutil.Process(pid)
            info = proc.info

            mem_info = info.get('memory_info')
            rss = mem_info.rss if mem_info else 0

            return ProcessInfo(
                pid=info['pid'],
                name=info.get('name', ''),
                username=info.get('username', 'unknown'),
                status=info.get('status', 'unknown'),
                cpu_percent=info.get('cpu_percent', 0) or 0,
                memory_percent=info.get('memory_percent', 0) or 0,
                memory_rss=rss,
                num_threads=info.get('num_threads', 1),
                create_time=info.get('create_time', 0),
                cmdline=info.get('cmdline', [])
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def kill_process(self, pid: int, force: bool = False) -> tuple[bool, str]:
        """Kill a process by PID"""
        try:
            proc = psutil.Process(pid)
            name = proc.name()

            # Check if it's a critical process
            critical_processes = ['init', 'systemd', 'kthreadd', 'sshd']
            if name in critical_processes:
                return False, f"Cannot kill critical process: {name}"

            # Try SIGTERM first (graceful)
            if not force:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                    return True, f"Process {pid} ({name}) terminated gracefully"
                except psutil.TimeoutExpired:
                    # Force kill if timeout
                    pass

            # SIGKILL (force)
            proc.kill()
            return True, f"Process {pid} ({name}) killed with SIGKILL"

        except psutil.NoSuchProcess:
            return False, f"Process {pid} not found"
        except psutil.AccessDenied:
            return False, f"Access denied to process {pid}"
        except Exception as e:
            return False, f"Error killing process {pid}: {str(e)}"

    def get_process_tree(self, pid: int) -> List[Dict]:
        """Get process tree for a given PID"""
        try:
            proc = psutil.Process(pid)
            tree = []

            def add_children(proc, level=0):
                try:
                    children = proc.children(recursive=True)
                    for child in children:
                        tree.append({
                            'pid': child.pid,
                            'name': child.name(),
                            'status': child.status(),
                            'level': level
                        })
                        add_children(child, level + 1)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            tree.append({
                'pid': proc.pid,
                'name': proc.name(),
                'status': proc.status(),
                'level': 0
            })
            add_children(proc)

            return tree
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return []

    def search_processes(self, query: str) -> List[ProcessInfo]:
        """Search processes by name or command line"""
        query_lower = query.lower()
        results = []

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                info = proc.info
                name = info.get('name', '').lower()
                cmdline = ' '.join(info.get('cmdline', [])).lower()

                if query_lower in name or query_lower in cmdline:
                    mem_info = info.get('memory_info')
                    rss = mem_info.rss if mem_info else 0

                    results.append(ProcessInfo(
                        pid=info['pid'],
                        name=info.get('name', ''),
                        username=info.get('username', 'unknown'),
                        status=info.get('status', 'unknown'),
                        cpu_percent=info.get('cpu_percent', 0) or 0,
                        memory_percent=info.get('memory_percent', 0) or 0,
                        memory_rss=rss,
                        num_threads=info.get('num_threads', 1),
                        create_time=info.get('create_time', 0),
                        cmdline=info.get('cmdline', [])
                    ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return results
