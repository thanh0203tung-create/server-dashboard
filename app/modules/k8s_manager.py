"""
Kubernetes Management Module
Manages Kubernetes resources including pods, services, deployments, and more
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import yaml

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False
    ApiException = Exception

class PodPhase(Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"

@dataclass
class PodInfo:
    name: str
    namespace: str
    status: PodPhase
    ready: str
    restarts: int
    age: str
    ip: str
    node: str
    containers: List[str]
    cpu_request: Optional[str] = None
    memory_request: Optional[str] = None
    cpu_limit: Optional[str] = None
    memory_limit: Optional[str] = None

@dataclass
class ServiceInfo:
    name: str
    namespace: str
    type: str
    cluster_ip: str
    external_ip: Optional[str]
    ports: List[str]
    selector: Dict[str, str]
    age: str

@dataclass
class DeploymentInfo:
    name: str
    namespace: str
    replicas: int
    available_replicas: int
    ready: str
    age: str
    images: List[str]

@dataclass
class NodeInfo:
    name: str
    status: str
    roles: List[str]
    age: str
    version: str
    cpu: str
    memory: str
    pods: int
    conditions: Dict[str, str]

class KubernetesManager:
    """Manage Kubernetes resources"""

    def __init__(self, namespace: str = "default", context: Optional[str] = None):
        self.namespace = namespace
        self.context = context
        self._core_v1 = None
        self._apps_v1 = None
        self._available = False
        self._error = None
        self._initialize()

    def _initialize(self):
        """Initialize Kubernetes client"""
        if not K8S_AVAILABLE:
            self._error = "kubernetes library not installed"
            return

        try:
            # Try in-cluster config first
            config.load_incluster_config()
        except Exception:
            try:
                # Try kubeconfig
                if self.context:
                    config.load_kube_config(context=self.context)
                else:
                    config.load_kube_config()
            except Exception as e:
                self._error = f"Failed to load kubeconfig: {str(e)}"
                return

        try:
            self._core_v1 = client.CoreV1Api()
            self._apps_v1 = client.AppsV1Api()
            self._available = True
        except Exception as e:
            self._error = f"Failed to initialize API: {str(e)}"

    @property
    def available(self) -> bool:
        return self._available

    def _parse_pod_phase(self, phase: str) -> PodPhase:
        """Parse pod phase"""
        phase_map = {
            "Pending": PodPhase.PENDING,
            "Running": PodPhase.RUNNING,
            "Succeeded": PodPhase.SUCCEEDED,
            "Failed": PodPhase.FAILED,
        }
        return phase_map.get(phase, PodPhase.UNKNOWN)

    def list_pods(self, namespace: Optional[str] = None) -> List[PodInfo]:
        """List pods in namespace"""
        if not self._available:
            return []

        ns = namespace or self.namespace

        try:
            pods = []
            ret = self._core_v1.list_namespaced_pod(ns, watch=False)

            for pod in ret.items:
                # Get container statuses
                container_statuses = pod.status.container_statuses or []
                restarts = sum(cs.restart_count for cs in container_statuses)

                # Check ready status
                ready = "0/0"
                if pod.status.conditions:
                    for condition in pod.status.conditions:
                        if condition.type == "Ready":
                            ready = "1/1" if condition.status == "True" else "0/1"
                            break

                # Get resource requests/limits
                cpu_req = None
                mem_req = None
                cpu_lim = None
                mem_lim = None
                containers_info = []

                for container in pod.spec.containers:
                    containers_info.append(container.name)
                    if container.resources.requests:
                        cpu_req = container.resources.requests.get('cpu')
                        mem_req = container.resources.requests.get('memory')
                    if container.resources.limits:
                        cpu_lim = container.resources.limits.get('cpu')
                        mem_lim = container.resources.limits.get('memory')

                pods.append(PodInfo(
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                    status=self._parse_pod_phase(pod.status.phase),
                    ready=ready,
                    restarts=restarts,
                    age=self._format_age(pod.metadata.creation_timestamp),
                    ip=pod.status.pod_ip or "",
                    node=pod.spec.node_name or "",
                    containers=containers_info,
                    cpu_request=str(cpu_req) if cpu_req else None,
                    memory_request=str(mem_req) if mem_req else None,
                    cpu_limit=str(cpu_lim) if cpu_lim else None,
                    memory_limit=str(mem_lim) if mem_lim else None
                ))

            return pods
        except ApiException as e:
            return []

    def list_services(self, namespace: Optional[str] = None) -> List[ServiceInfo]:
        """List services in namespace"""
        if not self._available:
            return []

        ns = namespace or self.namespace

        try:
            services = []
            ret = self._core_v1.list_namespaced_service(ns, watch=False)

            for svc in ret.items:
                # Get ports
                ports = []
                for port in svc.spec.ports:
                    port_str = f"{port.port}:{port.target_port}"
                    if port.node_port:
                        port_str += f":{port.node_port}"
                    if port.protocol and port.protocol != "TCP":
                        port_str += f"/{port.protocol}"
                    ports.append(port_str)

                # Get external IP
                external_ip = None
                if svc.status.load_balancer and svc.status.load_balancer.ingress:
                    external_ip = svc.status.load_balancer.ingress[0].ip

                services.append(ServiceInfo(
                    name=svc.metadata.name,
                    namespace=svc.metadata.namespace,
                    type=svc.spec.type,
                    cluster_ip=svc.spec.cluster_ip,
                    external_ip=external_ip,
                    ports=ports,
                    selector=svc.spec.selector or {},
                    age=self._format_age(svc.metadata.creation_timestamp)
                ))

            return services
        except ApiException:
            return []

    def list_deployments(self, namespace: Optional[str] = None) -> List[DeploymentInfo]:
        """List deployments in namespace"""
        if not self._available:
            return []

        ns = namespace or self.namespace

        try:
            deployments = []
            ret = self._apps_v1.list_namespaced_deployment(ns, watch=False)

            for deploy in ret.items:
                # Get images
                images = []
                for container in deploy.spec.template.spec.containers:
                    images.append(container.image)

                deployments.append(DeploymentInfo(
                    name=deploy.metadata.name,
                    namespace=deploy.metadata.namespace,
                    replicas=deploy.spec.replicas or 0,
                    available_replicas=deploy.status.available_replicas or 0,
                    ready=f"{deploy.status.ready_replicas or 0}/{deploy.spec.replicas or 0}",
                    age=self._format_age(deploy.metadata.creation_timestamp),
                    images=images
                ))

            return deployments
        except ApiException:
            return []

    def list_namespaces(self) -> List[str]:
        """List all namespaces"""
        if not self._available:
            return []

        try:
            ret = self._core_v1.list_namespace(watch=False)
            return [ns.metadata.name for ns in ret.items]
        except ApiException:
            return []

    def list_nodes(self) -> List[NodeInfo]:
        """List all cluster nodes"""
        if not self._available:
            return []

        try:
            nodes = []
            ret = self._core_v1.list_node(watch=False)

            for node in ret.items:
                # Get conditions
                conditions = {}
                if node.status.conditions:
                    for cond in node.status.conditions:
                        conditions[cond.type] = cond.status

                # Get allocatable resources
                allocatable = node.status.allocatable or {}
                cpu = allocatable.get('cpu', 'unknown')
                memory = allocatable.get('memory', 'unknown')
                pods = allocatable.get('pods', 'unknown')

                # Get roles
                roles = []
                for key, value in (node.metadata.labels or {}).items():
                    if key.startswith('node-role.kubernetes.io/'):
                        roles.append(key.split('/')[-1])
                    elif key == 'node.kubernetes.io/example':
                        pass

                nodes.append(NodeInfo(
                    name=node.metadata.name,
                    status="Ready" if conditions.get("Ready") == "True" else "NotReady",
                    roles=roles or ["worker"],
                    age=self._format_age(node.metadata.creation_timestamp),
                    version=node.status.node_info.kubelet_version,
                    cpu=cpu,
                    memory=memory,
                    pods=pods,
                    conditions=conditions
                ))

            return nodes
        except ApiException:
            return []

    def get_pod_logs(self, pod_name: str, namespace: Optional[str] = None,
                     container: Optional[str] = None, lines: int = 100) -> List[str]:
        """Get pod logs"""
        if not self._available:
            return ["Kubernetes not available"]

        ns = namespace or self.namespace

        try:
            logs = self._core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=ns,
                container=container,
                tail_lines=lines,
                timestamps=True
            )
            return logs.strip().split('\n')
        except ApiException as e:
            return [f"Failed to get logs: {str(e)}"]

    def delete_pod(self, pod_name: str, namespace: Optional[str] = None) -> tuple[bool, str]:
        """Delete a pod"""
        if not self._available:
            return False, "Kubernetes not available"

        ns = namespace or self.namespace

        try:
            self._core_v1.delete_namespaced_pod(
                name=pod_name,
                namespace=ns,
                body=client.V1DeleteOptions()
            )
            return True, f"Pod {pod_name} deleted"
        except ApiException as e:
            return False, f"Failed to delete pod: {str(e)}"

    def scale_deployment(self, name: str, replicas: int, namespace: Optional[str] = None) -> tuple[bool, str]:
        """Scale a deployment"""
        if not self._available:
            return False, "Kubernetes not available"

        ns = namespace or self.namespace

        try:
            body = {"spec": {"replicas": replicas}}
            self._apps_v1.patch_namespaced_deployment_scale(
                name=name,
                namespace=ns,
                body=body
            )
            return True, f"Deployment {name} scaled to {replicas} replicas"
        except ApiException as e:
            return False, f"Failed to scale deployment: {str(e)}"

    def get_cluster_info(self) -> Dict:
        """Get cluster information"""
        if not self._available:
            return {"available": False, "error": self._error}

        try:
            version = self._core_v1.get_api_resources()
            return {
                "available": True,
                "namespace": self.namespace,
                "nodes": len(self.list_nodes()),
                "namespaces": len(self.list_namespaces())
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def _format_age(self, timestamp) -> str:
        """Format timestamp to age string"""
        if not timestamp:
            return "unknown"

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        delta = now - timestamp

        if delta.days > 0:
            return f"{delta.days}d"
        elif delta.seconds >= 3600:
            return f"{delta.seconds // 3600}h"
        elif delta.seconds >= 60:
            return f"{delta.seconds // 60}m"
        else:
            return f"{delta.seconds}s"
