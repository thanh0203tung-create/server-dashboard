"""
Systemd Services Management Module
Manages systemd services on Ubuntu servers
"""

import subprocess
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class ServiceState(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    ACTIVATING = "activating"
    DEACTIVATING = "deactivating"
    UNKNOWN = "unknown"

@dataclass
class ServiceInfo:
    name: str
    load: str
    active: str
    sub: str
    description: str
    state: ServiceState
    pid: Optional[int] = None
    memory: Optional[str] = None
    cpu: Optional[str] = None

class ServiceManager:
    """Manage systemd services"""

    def __init__(self):
        self._cache = []
        self._cache_time = 0

    def _run_command(self, cmd: List[str]) -> tuple[bool, str]:
        """Run a shell command and return success status and output"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except FileNotFoundError:
            return False, "Command not found"
        except Exception as e:
            return False, str(e)

    def _parse_state(self, active: str, sub: str) -> ServiceState:
        """Parse service state from systemd output"""
        active_lower = active.lower()
        sub_lower = sub.lower()

        if active_lower == "active":
            if "running" in sub_lower:
                return ServiceState.ACTIVE
            elif "exited" in sub_lower:
                return ServiceState.ACTIVE
            elif "activating" in sub_lower:
                return ServiceState.ACTIVATING
        elif active_lower == "inactive":
            if "deactivating" in sub_lower:
                return ServiceState.DEACTIVATING
            return ServiceState.INACTIVE
        elif active_lower == "failed":
            return ServiceState.FAILED

        return ServiceState.UNKNOWN

    def list_services(self, state_filter: Optional[str] = None) -> List[ServiceInfo]:
        """List all services with optional state filter"""
        cmd = ["systemctl", "list-units", "--type=service", "--all",
               "--no-pager", "--no-legend",
               "--format=UNIT\tLOAD\tACTIVE\tSUB\tDESCRIPTION"]

        success, output = self._run_command(cmd)
        if not success:
            return []

        services = []
        for line in output.strip().split('\n'):
            if not line or '\t' not in line:
                continue

            parts = line.split('\t')
            if len(parts) < 5:
                continue

            name = parts[0].replace('.service', '')
            load = parts[1]
            active = parts[2]
            sub = parts[3]
            description = parts[4] if len(parts) > 4 else ""

            state = self._parse_state(active, sub)

            # Apply state filter
            if state_filter:
                if state_filter.lower() == "running" and state != ServiceState.ACTIVE:
                    continue
                elif state_filter.lower() == "failed" and state != ServiceState.FAILED:
                    continue
                elif state_filter.lower() == "stopped" and state != ServiceState.INACTIVE:
                    continue

            services.append(ServiceInfo(
                name=name,
                load=load,
                active=active,
                sub=sub,
                description=description,
                state=state
            ))

        return services

    def get_service_status(self, service_name: str) -> Optional[ServiceInfo]:
        """Get detailed status of a specific service"""
        if not service_name.endswith('.service'):
            service_name += '.service'

        cmd = ["systemctl", "status", service_name, "--no-pager"]
        success, output = self._run_command(cmd)

        if not success and "could not be found" in output.lower():
            return None

        # Parse the output
        lines = output.strip().split('\n')
        if not lines:
            return None

        # Parse service info from status output
        name = service_name.replace('.service', '')
        description = ""
        active = "unknown"
        sub = "unknown"
        load = "loaded"
        pid = None
        memory = None
        cpu = None

        for line in lines[1:]:
            if "Description:" in line:
                description = line.split("Description:", 1)[1].strip()
            elif "Active:" in line:
                active_part = line.split("Active:", 1)[1].strip()
                active, sub = active_part.split('(', 1) if '(' in active_part else (active_part, "")
                sub = sub.rstrip(')')

        state = self._parse_state(active, sub)

        return ServiceInfo(
            name=name,
            load=load,
            active=active,
            sub=sub,
            description=description,
            state=state,
            pid=pid,
            memory=memory,
            cpu=cpu
        )

    def start_service(self, service_name: str) -> tuple[bool, str]:
        """Start a systemd service"""
        if not service_name.endswith('.service'):
            service_name += '.service'

        success, output = self._run_command(["systemctl", "start", service_name])
        if success:
            return True, f"Service {service_name} started successfully"
        return False, f"Failed to start {service_name}: {output}"

    def stop_service(self, service_name: str) -> tuple[bool, str]:
        """Stop a systemd service"""
        if not service_name.endswith('.service'):
            service_name += '.service'

        success, output = self._run_command(["systemctl", "stop", service_name])
        if success:
            return True, f"Service {service_name} stopped successfully"
        return False, f"Failed to stop {service_name}: {output}"

    def restart_service(self, service_name: str) -> tuple[bool, str]:
        """Restart a systemd service"""
        if not service_name.endswith('.service'):
            service_name += '.service'

        success, output = self._run_command(["systemctl", "restart", service_name])
        if success:
            return True, f"Service {service_name} restarted successfully"
        return False, f"Failed to restart {service_name}: {output}"

    def reload_service(self, service_name: str) -> tuple[bool, str]:
        """Reload a systemd service"""
        if not service_name.endswith('.service'):
            service_name += '.service'

        success, output = self._run_command(["systemctl", "reload", service_name])
        if success:
            return True, f"Service {service_name} reloaded successfully"
        return False, f"Failed to reload {service_name}: {output}"

    def enable_service(self, service_name: str) -> tuple[bool, str]:
        """Enable a systemd service to start on boot"""
        if not service_name.endswith('.service'):
            service_name += '.service'

        success, output = self._run_command(["systemctl", "enable", service_name])
        if success:
            return True, f"Service {service_name} enabled successfully"
        return False, f"Failed to enable {service_name}: {output}"

    def disable_service(self, service_name: str) -> tuple[bool, str]:
        """Disable a systemd service from starting on boot"""
        if not service_name.endswith('.service'):
            service_name += '.service'

        success, output = self._run_command(["systemctl", "disable", service_name])
        if success:
            return True, f"Service {service_name} disabled successfully"
        return False, f"Failed to disable {service_name}: {output}"

    def get_service_logs(self, service_name: str, lines: int = 50) -> List[str]:
        """Get logs for a specific service using journalctl"""
        if not service_name.endswith('.service'):
            service_name += '.service'

        cmd = ["journalctl", "-u", service_name, "-n", str(lines), "--no-pager"]
        success, output = self._run_command(cmd)

        if success:
            return output.strip().split('\n')
        return [f"Failed to get logs: {output}"]

    def search_services(self, query: str) -> List[ServiceInfo]:
        """Search services by name or description"""
        all_services = self.list_services()
        query_lower = query.lower()

        return [
            s for s in all_services
            if query_lower in s.name.lower() or query_lower in s.description.lower()
        ]

    def get_service_count_by_state(self) -> Dict[str, int]:
        """Get count of services by state"""
        counts = {
            "active": 0,
            "inactive": 0,
            "failed": 0,
            "other": 0
        }

        for service in self.list_services():
            if service.state == ServiceState.ACTIVE:
                counts["active"] += 1
            elif service.state == ServiceState.INACTIVE:
                counts["inactive"] += 1
            elif service.state == ServiceState.FAILED:
                counts["failed"] += 1
            else:
                counts["other"] += 1

        return counts
