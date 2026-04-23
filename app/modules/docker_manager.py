"""
Docker Container Management Module
Manages Docker containers, images, volumes, and networks
"""

import docker
from docker.models.containers import Container
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class ContainerState(Enum):
    RUNNING = "running"
    PAUSED = "paused"
    RESTARTING = "restarting"
    EXITED = "exited"
    DEAD = "dead"
    CREATED = "created"
    REMOVING = "removing"
    UNKNOWN = "unknown"

@dataclass
class ContainerInfo:
    id: str
    short_id: str
    name: str
    image: str
    state: ContainerState
    status: str
    created: str
    ports: List[str]
    cpu_percent: float
    memory_usage: int
    memory_limit: int
    memory_percent: float
    network_mode: str

@dataclass
class ImageInfo:
    id: str
    short_id: str
    tags: List[str]
    size: int
    created: str

@dataclass
class VolumeInfo:
    name: str
    driver: str
    mountpoint: str
    scope: str

class DockerManager:
    """Manage Docker containers and resources"""

    def __init__(self):
        try:
            self.client = docker.from_env()
            self.client.ping()
            self.available = True
        except docker.errors.DockerException as e:
            self.client = None
            self.available = False
            self._error = str(e)

    def _parse_state(self, state: str) -> ContainerState:
        """Parse container state"""
        state_lower = state.lower()
        state_map = {
            "running": ContainerState.RUNNING,
            "paused": ContainerState.PAUSED,
            "restarting": ContainerState.RESTARTING,
            "exited": ContainerState.EXITED,
            "dead": ContainerState.DEAD,
            "created": ContainerState.CREATED,
            "removing": ContainerState.REMOVING,
        }
        return state_map.get(state_lower, ContainerState.UNKNOWN)

    def list_containers(self, all: bool = False) -> List[ContainerInfo]:
        """List all containers"""
        if not self.available:
            return []

        try:
            containers = []
            for container in self.client.containers.list(all=all):
                stats = self._get_container_stats(container)

                # Parse ports
                ports = []
                for port, bindings in container.ports.items():
                    if bindings:
                        for binding in bindings:
                            ports.append(f"{binding['HostIp']}:{binding['HostPort']}->{port}")
                    else:
                        ports.append(port)

                containers.append(ContainerInfo(
                    id=container.id,
                    short_id=container.short_id,
                    name=container.name,
                    image=container.image.tags[0] if container.image.tags else "<none>",
                    state=self._parse_state(container.status),
                    status=container.attrs.get('State', {}).get('Status', 'unknown'),
                    created=self._format_created(container.attrs.get('Created', '')),
                    ports=ports,
                    cpu_percent=stats['cpu_percent'],
                    memory_usage=stats['memory_usage'],
                    memory_limit=stats['memory_limit'],
                    memory_percent=stats['memory_percent'],
                    network_mode=container.attrs.get('HostConfig', {}).get('NetworkMode', 'unknown')
                ))

            # Sort by name
            containers.sort(key=lambda x: x.name)
            return containers
        except Exception as e:
            return []

    def _get_container_stats(self, container: Container) -> Dict:
        """Get container stats"""
        try:
            stats = container.stats(stream=False)
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            cpu_count = stats['cpu_stats'].get('online_cpus', 1)

            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0
            else:
                cpu_percent = 0.0

            memory_usage = stats['memory_stats'].get('usage', 0) or 0
            memory_limit = stats['memory_stats'].get('limit', 1) or 1
            memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0

            return {
                'cpu_percent': cpu_percent,
                'memory_usage': memory_usage,
                'memory_limit': memory_limit,
                'memory_percent': memory_percent
            }
        except Exception:
            return {
                'cpu_percent': 0,
                'memory_usage': 0,
                'memory_limit': 1,
                'memory_percent': 0
            }

    def _format_created(self, created: str) -> str:
        """Format creation time"""
        if not created:
            return "unknown"
        # Already formatted
        if isinstance(created, str):
            return created[:19]
        return str(created)

    def get_container(self, container_id: str) -> Optional[ContainerInfo]:
        """Get specific container by ID or name"""
        if not self.available:
            return None

        try:
            container = self.client.containers.get(container_id)
            return self._container_to_info(container)
        except docker.errors.NotFound:
            return None
        except Exception:
            return None

    def _container_to_info(self, container: Container) -> ContainerInfo:
        """Convert container to ContainerInfo"""
        stats = self._get_container_stats(container)

        ports = []
        for port, bindings in container.ports.items():
            if bindings:
                for binding in bindings:
                    ports.append(f"{binding['HostIp']}:{binding['HostPort']}->{port}")

        return ContainerInfo(
            id=container.id,
            short_id=container.short_id,
            name=container.name,
            image=container.image.tags[0] if container.image.tags else "<none>",
            state=self._parse_state(container.status),
            status=container.attrs.get('State', {}).get('Status', 'unknown'),
            created=self._format_created(container.attrs.get('Created', '')),
            ports=ports,
            cpu_percent=stats['cpu_percent'],
            memory_usage=stats['memory_usage'],
            memory_limit=stats['memory_limit'],
            memory_percent=stats['memory_percent'],
            network_mode=container.attrs.get('HostConfig', {}).get('NetworkMode', 'unknown')
        )

    def start_container(self, container_id: str) -> tuple[bool, str]:
        """Start a container"""
        if not self.available:
            return False, "Docker not available"

        try:
            container = self.client.containers.get(container_id)
            container.start()
            return True, f"Container {container.short_id} started"
        except docker.errors.NotFound:
            return False, f"Container {container_id} not found"
        except Exception as e:
            return False, f"Failed to start container: {str(e)}"

    def stop_container(self, container_id: str, timeout: int = 10) -> tuple[bool, str]:
        """Stop a container"""
        if not self.available:
            return False, "Docker not available"

        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=timeout)
            return True, f"Container {container.short_id} stopped"
        except docker.errors.NotFound:
            return False, f"Container {container_id} not found"
        except Exception as e:
            return False, f"Failed to stop container: {str(e)}"

    def restart_container(self, container_id: str) -> tuple[bool, str]:
        """Restart a container"""
        if not self.available:
            return False, "Docker not available"

        try:
            container = self.client.containers.get(container_id)
            container.restart()
            return True, f"Container {container.short_id} restarted"
        except docker.errors.NotFound:
            return False, f"Container {container_id} not found"
        except Exception as e:
            return False, f"Failed to restart container: {str(e)}"

    def pause_container(self, container_id: str) -> tuple[bool, str]:
        """Pause a container"""
        if not self.available:
            return False, "Docker not available"

        try:
            container = self.client.containers.get(container_id)
            container.pause()
            return True, f"Container {container.short_id} paused"
        except docker.errors.NotFound:
            return False, f"Container {container_id} not found"
        except Exception as e:
            return False, f"Failed to pause container: {str(e)}"

    def unpause_container(self, container_id: str) -> tuple[bool, str]:
        """Unpause a container"""
        if not self.available:
            return False, "Docker not available"

        try:
            container = self.client.containers.get(container_id)
            container.unpause()
            return True, f"Container {container.short_id} unpaused"
        except docker.errors.NotFound:
            return False, f"Container {container_id} not found"
        except Exception as e:
            return False, f"Failed to unpause container: {str(e)}"

    def remove_container(self, container_id: str, force: bool = False) -> tuple[bool, str]:
        """Remove a container"""
        if not self.available:
            return False, "Docker not available"

        try:
            container = self.client.containers.get(container_id)
            container.remove(force=force)
            return True, f"Container {container.short_id} removed"
        except docker.errors.NotFound:
            return False, f"Container {container_id} not found"
        except Exception as e:
            return False, f"Failed to remove container: {str(e)}"

    def get_container_logs(self, container_id: str, lines: int = 100) -> List[str]:
        """Get container logs"""
        if not self.available:
            return ["Docker not available"]

        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=lines, timestamps=True).decode('utf-8')
            return logs.strip().split('\n')
        except docker.errors.NotFound:
            return [f"Container {container_id} not found"]
        except Exception as e:
            return [f"Failed to get logs: {str(e)}"]

    def list_images(self) -> List[ImageInfo]:
        """List all images"""
        if not self.available:
            return []

        try:
            images = []
            for image in self.client.images.list():
                images.append(ImageInfo(
                    id=image.id,
                    short_id=image.short_id,
                    tags=image.tags if image.tags else ["<none>"],
                    size=image.attrs.get('Size', 0),
                    created=image.attrs.get('Created', '')[:10]
                ))
            return images
        except Exception:
            return []

    def list_volumes(self) -> List[VolumeInfo]:
        """List all volumes"""
        if not self.available:
            return []

        try:
            volumes = []
            for volume in self.client.volumes.list():
                volumes.append(VolumeInfo(
                    name=volume.name,
                    driver=volume.attrs.get('Driver', 'local'),
                    mountpoint=volume.attrs.get('Mountpoint', ''),
                    scope=volume.attrs.get('Scope', 'local')
                ))
            return volumes
        except Exception:
            return []

    def get_docker_info(self) -> Dict:
        """Get Docker system info"""
        if not self.available:
            return {"available": False, "error": self._error}

        try:
            info = self.client.info()
            return {
                "available": True,
                "version": self.client.version()['Version'],
                "containers": info.get('Containers', 0),
                "running": info.get('ContainersRunning', 0),
                "paused": info.get('ContainersPaused', 0),
                "stopped": info.get('ContainersStopped', 0),
                "images": info.get('Images', 0),
                "memory_total": info.get('MemTotal', 0),
                "cpus": info.get('NCPU', 0),
                "os": info.get('OperatingSystem', ''),
                "kernel": info.get('KernelVersion', '')
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    @staticmethod
    def format_size(size: int) -> str:
        """Format size in bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
