"""
Main Server Dashboard Application
A beautiful TUI application for monitoring and managing Ubuntu servers
"""

import urwid
import asyncio
import time
from typing import Dict, List, Optional, Any

from app.modules.system_monitor import SystemMonitor
from app.modules.process_monitor import ProcessMonitor, ProcessInfo
from app.modules.service_manager import ServiceManager, ServiceInfo, ServiceState
from app.modules.docker_manager import DockerManager, ContainerInfo, ContainerState
from app.modules.k8s_manager import KubernetesManager, PodInfo, PodPhase
from app.modules.log_viewer import LogViewer, LogEntry, LogLevel
from app.ui.colors import Colors, Theme

class ServerDashboardApp:
    """Main application class for the Server Dashboard"""

    # Screen definitions
    SCREEN_SYSTEM = 0
    SCREEN_PROCESSES = 1
    SCREEN_SERVICES = 2
    SCREEN_DOCKER = 3
    SCREEN_KUBERNETES = 4
    SCREEN_LOGS = 5
    SCREEN_HELP = 6

    def __init__(self):
        self.loop = None
        self.palette = self._create_palette()

        # Initialize managers
        self.system_monitor = SystemMonitor()
        self.process_monitor = ProcessMonitor()
        self.service_manager = ServiceManager()
        self.docker_manager = DockerManager()
        self.k8s_manager = KubernetesManager()
        self.log_viewer = LogViewer()

        # UI state
        self.current_screen = self.SCREEN_SYSTEM
        self.screen_data: Dict[int, Any] = {}
        self.last_refresh: Dict[int, float] = {}

        # Refresh intervals (seconds)
        self.refresh_intervals = {
            self.SCREEN_SYSTEM: 2,
            self.SCREEN_PROCESSES: 3,
            self.SCREEN_SERVICES: 5,
            self.SCREEN_DOCKER: 5,
            self.SCREEN_KUBERNETES: 5,
            self.SCREEN_LOGS: 0,  # Manual
            self.SCREEN_HELP: 0,
        }

        # Build UI
        self.header = None
        self.content = None
        self.footer = None
        self.main_frame = None
        self._build_ui()

    def _create_palette(self) -> List[tuple]:
        """Create color palette for urwid"""
        return [
            # Standard colors
            ('body', 'light gray', 'black'),
            ('header', 'white', 'dark blue'),
            ('footer', 'light gray', 'dark gray'),
            ('selected', 'black', 'light gray'),
            ('button', 'light gray', 'dark blue'),
            ('button:focus', 'white', 'dark blue'),

            # Status colors
            ('success', 'white', 'dark green'),
            ('warning', 'black', 'yellow'),
            ('error', 'white', 'dark red'),
            ('info', 'white', 'dark cyan'),

            # CPU/Memory colors
            ('cpu-low', 'white', 'dark green'),
            ('cpu-medium', 'black', 'yellow'),
            ('cpu-high', 'white', 'dark red'),
            ('mem-low', 'white', 'dark green'),
            ('mem-medium', 'black', 'yellow'),
            ('mem-high', 'white', 'dark red'),

            # Service colors
            ('running', 'white', 'dark green'),
            ('stopped', 'light gray', 'black'),
            ('failed', 'white', 'dark red'),
            ('paused', 'black', 'yellow'),

            # Menu
            ('menu-active', 'white', 'dark blue'),
            ('menu-inactive', 'light gray', 'black'),

            # Log levels
            ('log-debug', 'light gray', 'black'),
            ('log-info', 'white', 'black'),
            ('log-warning', 'yellow', 'black'),
            ('log-error', 'light red', 'black'),
            ('log-critical', 'white', 'dark red'),
        ]

    def _build_ui(self):
        """Build the main UI components"""
        # Header
        self.header = urwid.Columns([
            urwid.Text(('header', ' [ SERVER DASHBOARD ] '), align='center'),
            urwid.Text(('footer', ''), align='right'),
        ], dividechars=1)

        # Build menu
        menu_items = self._build_menu()

        # Content area
        self.content = urwid.LineBox(
            urwid.Padding(urwid.Text('Loading...'), left=1, right=1),
            title='',
            title_attr='header'
        )

        # Footer
        self.footer = urwid.Text(('footer', ' q: Quit | Enter: Select | r: Refresh | k: Kill process/service | c: Container actions '), align='center')

        # Main frame
        self.main_frame = urwid.Frame(
            header=urwid.Pile([self.header]),
            body=urwid.Columns([
                (20, urwid.LineBox(urwid.Pile(menu_items), title='[ Menu ]')),
                self.content,
            ], dividechars=1),
            footer=self.footer
        )

    def _build_menu(self) -> List[urwid.Widget]:
        """Build the menu items"""
        menu_defs = [
            ('System', self.SCREEN_SYSTEM, 's'),
            ('Processes', self.SCREEN_PROCESSES, 'p'),
            ('Services', self.SCREEN_SERVICES, 'v'),
            ('Docker', self.SCREEN_DOCKER, 'd'),
            ('Kubernetes', self.SCREEN_KUBERNETES, 'k'),
            ('Logs', self.SCREEN_LOGS, 'l'),
            ('Help', self.SCREEN_HELP, 'h'),
        ]

        items = []
        for name, screen, key in menu_defs:
            focus = self.current_screen == screen
            attr = 'menu-active' if focus else 'menu-inactive'
            item = urwid.AttrWrap(
                urwid.Text(f' {name} ({key})', align='left'),
                attr
            )
            items.append(item)

        return items

    def refresh_menu(self):
        """Refresh the menu to update focus"""
        menu_items = self._build_menu()

        # Find and replace the menu pile
        cols = self.main_frame.body
        if isinstance(cols, urwid.Columns):
            menu_widget = cols.contents[0][0]
            if hasattr(menu_widget, 'original_widget'):
                menu_widget.original_widget.contents = [
                    (item, ('pack', None)) for item in menu_items
                ]

    def update_header(self):
        """Update header with current system info"""
        try:
            cpu = self.system_monitor.get_cpu_info()
            mem = self.system_monitor.get_memory_info()
            uptime = self.system_monitor.get_uptime()

            left_text = f' CPU: {cpu.percent:.1f}% | RAM: {mem.percent:.1f}% | Uptime: {uptime} '
        except Exception:
            left_text = ' Loading... '

        if isinstance(self.header, urwid.Columns):
            self.header.contents[0] = (urwid.Text(('header', left_text), align='center'), self.header.contents[0][1])
            self.header.contents[1] = (urwid.Text(('footer', time.strftime(' %H:%M:%S ')), align='right'), self.header.contents[1][1])

    def _should_refresh(self, screen: int) -> bool:
        """Check if a screen should be refreshed"""
        if screen not in self.last_refresh:
            return True

        interval = self.refresh_intervals.get(screen, 5)
        if interval == 0:  # Manual refresh
            return False

        return time.time() - self.last_refresh[screen] >= interval

    def _mark_refreshed(self, screen: int):
        """Mark a screen as refreshed"""
        self.last_refresh[screen] = time.time()

    def render_screen(self, screen: int):
        """Render the content for a specific screen"""
        renderers = {
            self.SCREEN_SYSTEM: self._render_system_screen,
            self.SCREEN_PROCESSES: self._render_processes_screen,
            self.SCREEN_SERVICES: self._render_services_screen,
            self.SCREEN_DOCKER: self._render_docker_screen,
            self.SCREEN_KUBERNETES: self._render_k8s_screen,
            self.SCREEN_LOGS: self._render_logs_screen,
            self.SCREEN_HELP: self._render_help_screen,
        }

        renderer = renderers.get(screen, self._render_default_screen)
        widget = renderer()

        self.content = urwid.LineBox(
            urwid.Padding(widget, left=1, right=1),
            title=self._get_screen_title(screen),
            title_attr='header'
        )

        if isinstance(self.main_frame.body, urwid.Columns):
            self.main_frame.body.contents[1] = (self.content, ('weight', 80))

    def _get_screen_title(self, screen: int) -> str:
        """Get title for a screen"""
        titles = {
            self.SCREEN_SYSTEM: 'System Overview',
            self.SCREEN_PROCESSES: 'Process Monitor',
            self.SCREEN_SERVICES: 'Systemd Services',
            self.SCREEN_DOCKER: 'Docker Containers',
            self.SCREEN_KUBERNETES: 'Kubernetes',
            self.SCREEN_LOGS: 'Log Viewer',
            self.SCREEN_HELP: 'Help & Shortcuts',
        }
        return titles.get(screen, 'Dashboard')

    def _render_default_screen(self) -> urwid.Widget:
        """Default screen renderer"""
        return urwid.Text('Unknown screen')

    def _render_system_screen(self) -> urwid.Widget:
        """Render system overview screen"""
        try:
            summary = self.system_monitor.get_system_summary()
            cpu = summary['cpu']
            mem = summary['memory']
            swap = summary['swap']
            disks = summary['disks']
            hostname = summary['hostname']

            lines = []

            # Header
            lines.append(urwid.Text(('header', f'=== System Information ({hostname}) ===')))

            # CPU Section
            cpu_color = Theme.get_cpu_color(cpu.percent)
            lines.append(urwid.Text(''))
            lines.append(urwid.Text(('header', ' CPU Information')))
            lines.append(urwid.Text(f'  Usage: {cpu.percent:.1f}%'))
            lines.append(urwid.Text(f'  Cores: {cpu.cores}'))
            lines.append(urwid.Text(f'  Frequency: {cpu.freq:.0f} MHz'))
            lines.append(urwid.Text(f'  Load Average (1/5/15 min): {cpu.load_avg[0]:.2f} / {cpu.load_avg[1]:.2f} / {cpu.load_avg[2]:.2f}'))

            # Memory Section
            mem_color = Theme.get_memory_color(mem.percent)
            lines.append(urwid.Text(''))
            lines.append(urwid.Text(('header', ' Memory Information')))
            lines.append(urwid.Text(f'  Total: {SystemMonitor.format_bytes(mem.total)}'))
            lines.append(urwid.Text(f'  Used: {SystemMonitor.format_bytes(mem.used)} ({mem.percent:.1f}%)'))
            lines.append(urwid.Text(f'  Available: {SystemMonitor.format_bytes(mem.available)}'))

            # Swap Section
            lines.append(urwid.Text(''))
            lines.append(urwid.Text(('header', ' Swap Information')))
            lines.append(urwid.Text(f'  Total: {SystemMonitor.format_bytes(swap.total)}'))
            lines.append(urwid.Text(f'  Used: {SystemMonitor.format_bytes(swap.used)} ({swap.percent:.1f}%)'))

            # Disk Section
            lines.append(urwid.Text(''))
            lines.append(urwid.Text(('header', ' Disk Information')))
            for disk in disks:
                lines.append(urwid.Text(f'  {disk.mountpoint}: {SystemMonitor.format_bytes(disk.used)} / {SystemMonitor.format_bytes(disk.total)} ({disk.percent:.1f}%)'))

            # Uptime
            lines.append(urwid.Text(''))
            lines.append(urwid.Text(('footer', f'  System Uptime: {summary["uptime"]}')))

            return urwid.ListBox(urwid.SimpleListWalker(lines))

        except Exception as e:
            return urwid.Text(f'Error loading system info: {str(e)}')

    def _render_processes_screen(self) -> urwid.Widget:
        """Render processes screen"""
        try:
            processes = self.process_monitor.get_all_processes(min_cpu=0.5, min_mem=0.1)
            lines = []

            # Header
            lines.append(urwid.Text(('header', ' PID    NAME                    USER         CPU%    MEM%    STATUS')))
            lines.append(urwid.Text(('footer', '-' * 80)))

            for proc in processes[:50]:  # Limit to 50 processes
                status_color = 'info'
                if proc.status == 'running':
                    status_color = 'success'
                elif proc.status == 'zombie':
                    status_color = 'error'

                cpu_color = Theme.get_cpu_color(proc.cpu_percent)
                mem_color = Theme.get_memory_color(proc.memory_percent)

                line = f' {proc.pid:<6} {proc.name[:23]:<23} {proc.username[:10]:<10} {proc.cpu_percent:>5.1f}  {proc.memory_percent:>5.1f}  {proc.status}'
                lines.append(urwid.Text(line))

            lines.append(urwid.Text(''))
            lines.append(urwid.Text(('footer', f' Total processes shown: {len(processes)}. Press k to kill a process.')))

            return urwid.ListBox(urwid.SimpleListWalker(lines))

        except Exception as e:
            return urwid.Text(f'Error loading processes: {str(e)}')

    def _render_services_screen(self) -> urwid.Widget:
        """Render services screen"""
        try:
            services = self.service_manager.list_services()
            lines = []

            # Count by state
            counts = self.service_manager.get_service_count_by_state()

            lines.append(urwid.Text(('header', f'=== Service Status ===')))
            lines.append(urwid.Text(f'  Running: ({counts["active"]}) | Stopped: ({counts["inactive"]}) | Failed: ({counts["failed"]})'))
            lines.append(urwid.Text(''))
            lines.append(urwid.Text(('header', ' UNIT                         STATE      SUB         DESCRIPTION')))
            lines.append(urwid.Text(('footer', '-' * 90)))

            for svc in services[:60]:
                state_color = Theme.get_service_color(svc.active)
                state_str = f'{svc.active:<8} {svc.sub:<10}'

                line = f' {svc.name:<26} {state_str:<20} {svc.description[:30]}'
                lines.append(urwid.Text(line))

            lines.append(urwid.Text(''))
            lines.append(urwid.Text(('footer', f' Total services: {len(services)}. Press Enter to manage a service.')))

            return urwid.ListBox(urwid.SimpleListWalker(lines))

        except Exception as e:
            return urwid.Text(f'Error loading services: {str(e)}')

    def _render_docker_screen(self) -> urwid.Widget:
        """Render Docker containers screen"""
        try:
            containers = self.docker_manager.list_containers()
            info = self.docker_manager.get_docker_info()
            lines = []

            if not self.docker_manager.available:
                lines.append(urwid.Text(('error', ' Docker is not available or not running.')))
                lines.append(urwid.Text(''))
                if 'error' in info:
                    lines.append(urwid.Text(f' Reason: {info["error"]}'))
                return urwid.ListBox(urwid.SimpleListWalker(lines))

            # Docker info
            lines.append(urwid.Text(('header', f'=== Docker Status ===')))
            lines.append(urwid.Text(f'  Version: {info.get("version", "unknown")} | Running: {info.get("running", 0)} | Stopped: {info.get("stopped", 0)} | Images: {info.get("images", 0)}'))
            lines.append(urwid.Text(''))
            lines.append(urwid.Text(('header', ' CONTAINER ID   NAME                IMAGE                 STATUS        CPU%    MEM%')))
            lines.append(urwid.Text(('footer', '-' * 95)))

            for container in containers:
                state_color = Theme.get_container_color(container.status)

                line = f' {container.short_id:<14} {container.name[:19]:<19} {container.image[:20]:<20} {container.status:<13} {container.cpu_percent:>5.1f}  {container.memory_percent:>5.1f}'
                lines.append(urwid.Text(line))

                # Show ports if any
                if container.ports:
                    ports_str = ', '.join(container.ports[:3])
                    if len(container.ports) > 3:
                        ports_str += '...'
                    lines.append(urwid.Text(f'    Ports: {ports_str}'))

            if not containers:
                lines.append(urwid.Text('  No containers found.'))

            lines.append(urwid.Text(''))
            lines.append(urwid.Text(('footer', f' Press Enter to manage a container. ')))

            return urwid.ListBox(urwid.SimpleListWalker(lines))

        except Exception as e:
            return urwid.Text(f'Error loading Docker info: {str(e)}')

    def _render_k8s_screen(self) -> urwid.Widget:
        """Render Kubernetes screen"""
        try:
            lines = []

            if not self.k8s_manager.available:
                lines.append(urwid.Text(('error', ' Kubernetes is not available or not configured.')))
                lines.append(urwid.Text(''))
                if self.k8s_manager._error:
                    lines.append(urwid.Text(f' Reason: {self.k8s_manager._error}'))
                lines.append(urwid.Text(''))
                lines.append(urwid.Text(' To configure Kubernetes, ensure:'))
                lines.append(urwid.Text('  1. kubectl is installed and configured'))
                lines.append(urwid.Text('  2. kubeconfig is available at ~/.kube/config'))
                lines.append(urwid.Text('  3. Python kubernetes package is installed'))
                return urwid.ListBox(urwid.SimpleListWalker(lines))

            # Pods section
            pods = self.k8s_manager.list_pods()
            namespaces = self.k8s_manager.list_namespaces()
            nodes = self.k8s_manager.list_nodes()

            lines.append(urwid.Text(('header', f'=== Kubernetes Cluster ===')))
            lines.append(urwid.Text(f'  Namespace: {self.k8s_manager.namespace} | Nodes: {len(nodes)} | Namespaces: {len(namespaces)}'))
            lines.append(urwid.Text(''))
            lines.append(urwid.Text(('header', ' POD NAME                       READY    STATUS    RESTARTS  AGE')))
            lines.append(urwid.Text(('footer', '-' * 75)))

            for pod in pods[:30]:
                phase_color = 'info'
                if pod.status == PodPhase.RUNNING:
                    phase_color = 'success'
                elif pod.status == PodPhase.FAILED:
                    phase_color = 'error'
                elif pod.status == PodPhase.PENDING:
                    phase_color = 'warning'

                line = f' {pod.name[:29]:<29} {pod.ready:<8} {pod.status.value:<9} {pod.restarts:<9} {pod.age}'
                lines.append(urwid.Text(line))

                if pod.containers:
                    lines.append(urwid.Text(f'    Containers: {", ".join(pod.containers)}'))

            if not pods:
                lines.append(urwid.Text('  No pods found in namespace.'))

            lines.append(urwid.Text(''))
            lines.append(urwid.Text(('footer', f' Total pods: {len(pods)}. Press Enter to manage.')))

            return urwid.ListBox(urwid.SimpleListWalker(lines))

        except Exception as e:
            return urwid.Text(f'Error loading Kubernetes info: {str(e)}')

    def _render_logs_screen(self) -> urwid.Widget:
        """Render log viewer screen"""
        try:
            # Get logs from journalctl
            log_entries = self.log_viewer.read_journalctl(lines=50)
            lines = []

            lines.append(urwid.Text(('header', '=== System Logs (journalctl -n 50) ===')))
            lines.append(urwid.Text(''))

            for entry in log_entries[-50:]:
                level_color = Theme.get_log_level_color(entry.level.value)
                line = f'[{entry.timestamp[:19]}] {entry.message}'
                lines.append(urwid.Text(line, attr=level_color))

            lines.append(urwid.Text(''))
            lines.append(urwid.Text(('footer', ' Press l to search logs, f to filter by level. ')))

            return urwid.ListBox(urwid.SimpleListWalker(lines))

        except Exception as e:
            return urwid.Text(f'Error loading logs: {str(e)}')

    def _render_help_screen(self) -> urwid.Widget:
        """Render help screen"""
        lines = []

        lines.append(urwid.Text(('header', '=== Server Dashboard - Help & Shortcuts ===')))
        lines.append(urwid.Text(''))

        shortcuts = [
            ('General', [
                ('q / Ctrl+C', 'Quit the application'),
                ('r', 'Refresh current screen'),
                ('1-7', 'Jump to specific screen'),
            ]),
            ('System/Processes', [
                ('s', 'System overview'),
                ('p', 'Process list'),
                ('k', 'Kill a process'),
            ]),
            ('Services', [
                ('v', 'View services'),
                ('Enter', 'Manage selected service'),
                ('s', 'Start service'),
                ('t', 'Stop service'),
                ('r', 'Restart service'),
            ]),
            ('Docker', [
                ('d', 'Docker containers'),
                ('Enter', 'Manage container'),
                ('s', 'Start container'),
                ('t', 'Stop container'),
                ('r', 'Restart container'),
            ]),
            ('Kubernetes', [
                ('K', 'Kubernetes pods'),
                ('Enter', 'View pod details'),
                ('l', 'Get pod logs'),
                ('d', 'Delete pod'),
            ]),
            ('Logs', [
                ('l', 'Log viewer'),
                ('/', 'Search logs'),
                ('f', 'Filter by level'),
                ('e', 'Export logs'),
            ]),
        ]

        for section, items in shortcuts:
            lines.append(urwid.Text(('header', f' {section}')))
            for key, desc in items:
                lines.append(urwid.Text(f'   {key:<15} {desc}'))
            lines.append(urwid.Text(''))

        lines.append(urwid.Text(('footer', ' Press any key to return to the dashboard.')))

        return urwid.ListBox(urwid.SimpleListWalker(lines))

    def handle_input(self, key: str) -> bool:
        """Handle keyboard input. Returns True if input was handled."""
        # Quit
        if key in ('q', 'Q', 'ctrl c', 'ctrl C'):
            raise urwid.ExitMainLoop()

        # Navigation shortcuts
        nav_keys = {
            's': self.SCREEN_SYSTEM,
            'p': self.SCREEN_PROCESSES,
            'v': self.SCREEN_SERVICES,
            'd': self.SCREEN_DOCKER,
            '1': self.SCREEN_SYSTEM,
            '2': self.SCREEN_PROCESSES,
            '3': self.SCREEN_SERVICES,
            '4': self.SCREEN_DOCKER,
            '5': self.SCREEN_KUBERNETES,
            '6': self.SCREEN_LOGS,
            '7': self.SCREEN_HELP,
        }

        if key in nav_keys:
            self.current_screen = nav_keys[key]
            self.refresh_menu()
            self.render_screen(self.current_screen)
            self._mark_refreshed(self.current_screen)
            return True

        # K key for Kubernetes (uppercase to differentiate from k for kill)
        if key == 'K':
            self.current_screen = self.SCREEN_KUBERNETES
            self.refresh_menu()
            self.render_screen(self.current_screen)
            self._mark_refreshed(self.current_screen)
            return True

        # Refresh
        if key in ('r', 'R'):
            self._mark_refreshed(self.current_screen)
            self.render_screen(self.current_screen)
            return True

        # Help
        if key in ('h', 'H', '?'):
            self.current_screen = self.SCREEN_HELP
            self.refresh_menu()
            self.render_screen(self.current_screen)
            return True

        # Logs
        if key in ('l', 'L'):
            if self.current_screen != self.SCREEN_LOGS:
                self.current_screen = self.SCREEN_LOGS
                self.refresh_menu()
            self.render_screen(self.current_screen)
            return True

        # Kill process (on process screen)
        if key in ('k', 'K'):
            if self.current_screen == self.SCREEN_PROCESSES:
                # Get top CPU process and kill it (demo)
                self._show_kill_dialog()
                return True

        # Enter key for actions
        if key == 'enter':
            self._handle_enter()
            return True

        # Auto-refresh on screens that need it
        if self._should_refresh(self.current_screen):
            self.render_screen(self.current_screen)
            self._mark_refreshed(self.current_screen)

        return False

    def _show_kill_dialog(self):
        """Show kill process dialog"""
        # This would show a dialog - simplified for now
        processes = self.process_monitor.get_top_cpu_processes(5)
        if processes:
            proc = processes[0]
            success, msg = self.process_monitor.kill_process(proc.pid, force=False)
            self.footer.set_text(('footer', msg))
        else:
            self.footer.set_text(('footer', 'No processes to kill'))

    def _handle_enter(self):
        """Handle Enter key press"""
        if self.current_screen == self.SCREEN_DOCKER:
            # Cycle through container actions
            containers = self.docker_manager.list_containers()
            if containers:
                container = containers[0]
                if container.state == ContainerState.RUNNING:
                    self.docker_manager.stop_container(container.id)
                else:
                    self.docker_manager.start_container(container.id)
                self.render_screen(self.current_screen)

    def update(self, user_data=None):
        """Periodic update callback"""
        self.update_header()

        # Auto-refresh current screen if needed
        if self._should_refresh(self.current_screen):
            self.render_screen(self.current_screen)
            self._mark_refreshed(self.current_screen)

        # Schedule next update
        if self.loop:
            self.loop.set_alarm_in(1, self.update)

    def run(self):
        """Run the application"""
        self.loop = urwid.MainLoop(
            self.main_frame,
            palette=self.palette,
            unhandled_input=self.handle_input,
            handle_mouse=False
        )

        # Initial render
        self.update_header()
        self.render_screen(self.current_screen)

        # Start periodic updates
        self.loop.set_alarm_in(1, self.update)

        try:
            self.loop.run()
        except KeyboardInterrupt:
            pass
        except urwid.ExitMainLoop:
            pass

        print('\n\nGoodbye! Thanks for using Server Dashboard.\n')
