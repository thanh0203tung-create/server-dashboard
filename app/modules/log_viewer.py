"""
Log Viewer Module
Views and manages system logs, service logs, and application logs
"""

import os
import re
import subprocess
from typing import List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    ALERT = "ALERT"
    EMERGENCY = "EMERGENCY"
    UNKNOWN = "UNKNOWN"

@dataclass
class LogEntry:
    timestamp: str
    level: LogLevel
    source: str
    message: str
    raw: str

class LogViewer:
    """View and manage system logs"""

    def __init__(self):
        self.default_log_paths = {
            'syslog': '/var/log/syslog',
            'auth': '/var/log/auth.log',
            'kern': '/var/log/kern.log',
            'dmesg': '/var/log/dmesg',
            'apt': '/var/log/apt/history.log',
            'dpkg': '/var/log/dpkg.log',
            'nginx': '/var/log/nginx/access.log',
            'nginx_error': '/var/log/nginx/error.log',
            'apache': '/var/log/apache2/access.log',
            'apache_error': '/var/log/apache2/error.log',
            'mysql': '/var/log/mysql/error.log',
            'postgresql': '/var/log/postgresql/postgresql.log',
            'docker': '/var/log/docker.log',
            'kubernetes': '/var/log/kubernetes.log'
        }

        self._level_pattern = re.compile(
            r'\b(DEBUG|INFO|NOTICE|WARNING|WARN|ERROR|ERR|CRITICAL|CRIT|ALERT|EMERGENCY|PANIC)\b',
            re.IGNORECASE
        )

        self._timestamp_patterns = [
            r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}',  # Syslog format
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',   # ISO format
            r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', # Common format
        ]

    def _parse_log_level(self, text: str) -> LogLevel:
        """Parse log level from text"""
        match = self._level_pattern.search(text)
        if match:
            level_str = match.group(1).upper()
            level_map = {
                'DEBUG': LogLevel.DEBUG,
                'INFO': LogLevel.INFO,
                'NOTICE': LogLevel.INFO,
                'WARNING': LogLevel.WARNING,
                'WARN': LogLevel.WARNING,
                'ERROR': LogLevel.ERROR,
                'ERR': LogLevel.ERROR,
                'CRITICAL': LogLevel.CRITICAL,
                'CRIT': LogLevel.CRITICAL,
                'ALERT': LogLevel.ALERT,
                'EMERGENCY': LogLevel.EMERGENCY,
                'PANIC': LogLevel.EMERGENCY,
            }
            return level_map.get(level_str, LogLevel.UNKNOWN)
        return LogLevel.UNKNOWN

    def _parse_timestamp(self, line: str) -> str:
        """Extract timestamp from log line"""
        for pattern in self._timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(0)
        return ""

    def read_log_file(self, path: str, lines: int = 100, offset: int = 0) -> List[LogEntry]:
        """Read log entries from a file"""
        entries = []

        if not os.path.exists(path):
            return [LogEntry(
                timestamp="",
                level=LogLevel.ERROR,
                source="",
                message=f"Log file not found: {path}",
                raw=f"Log file not found: {path}"
            )]

        try:
            # Use tail to read last N lines efficiently
            cmd = ['tail', '-n', str(lines + offset), path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return [LogEntry(
                    timestamp="",
                    level=LogLevel.ERROR,
                    source="",
                    message=f"Failed to read log: {result.stderr}",
                    raw=f"Error: {result.stderr}"
                )]

            all_lines = result.stdout.strip().split('\n')

            # Apply offset
            if offset > 0 and offset < len(all_lines):
                all_lines = all_lines[offset:]

            for line in all_lines:
                if not line.strip():
                    continue

                timestamp = self._parse_timestamp(line)
                level = self._parse_log_level(line)

                # Try to extract source (usually hostname or program name)
                source = ""
                parts = line.split()
                if len(parts) >= 2:
                    # Common syslog format: month day time hostname program
                    if ':' in parts[-1] or any(c.isalpha() for c in parts[1]):
                        source = parts[1] if len(parts) > 1 else ""

                entries.append(LogEntry(
                    timestamp=timestamp,
                    level=level,
                    source=source,
                    message=line,
                    raw=line
                ))

            return entries

        except PermissionError:
            return [LogEntry(
                timestamp="",
                level=LogLevel.ERROR,
                source="",
                message="Permission denied. Try running with sudo.",
                raw="Permission denied"
            )]
        except Exception as e:
            return [LogEntry(
                timestamp="",
                level=LogLevel.ERROR,
                source="",
                message=f"Error reading log: {str(e)}",
                raw=f"Error: {str(e)}"
            )]

    def read_journalctl(self, lines: int = 100, unit: Optional[str] = None,
                        priority: Optional[str] = None, since: Optional[str] = None) -> List[LogEntry]:
        """Read logs using journalctl"""
        cmd = ['journalctl', '-n', str(lines), '--no-pager', '--format=short-iso']

        if unit:
            cmd.extend(['-u', unit])

        if priority:
            cmd.extend(['-p', priority])

        if since:
            cmd.extend(['--since', since])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0 and result.stderr:
                return [LogEntry(
                    timestamp="",
                    level=LogLevel.ERROR,
                    source="",
                    message=f"journalctl error: {result.stderr}",
                    raw=result.stderr
                )]

            entries = []
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue

                timestamp = self._parse_timestamp(line)
                level = self._parse_log_level(line)

                # Extract source
                source = ""
                parts = line.split()
                if len(parts) >= 2:
                    source = parts[1] if ':' not in parts[0] else ""

                entries.append(LogEntry(
                    timestamp=timestamp,
                    level=level,
                    source=source,
                    message=line,
                    raw=line
                ))

            return entries

        except FileNotFoundError:
            return [LogEntry(
                timestamp="",
                level=LogLevel.ERROR,
                source="",
                message="journalctl not found. This system may not use systemd.",
                raw="journalctl not available"
            )]
        except Exception as e:
            return [LogEntry(
                timestamp="",
                level=LogLevel.ERROR,
                source="",
                message=f"Error reading journalctl: {str(e)}",
                raw=f"Error: {str(e)}"
            )]

    def read_dmesg(self, lines: int = 100) -> List[LogEntry]:
        """Read kernel ring buffer logs"""
        try:
            result = subprocess.run(
                ['dmesg', '-T', '-n', '7', '-w'],  # -w for watch, but we just want recent
                capture_output=True,
                text=True,
                timeout=10
            )

            # dmesg -T formats with time, use regular dmesg for parsing
            result_raw = subprocess.run(
                ['dmesg'],
                capture_output=True,
                text=True,
                timeout=10
            )

            entries = []
            all_lines = result_raw.stdout.strip().split('\n')

            # Get last N lines
            for line in all_lines[-lines:]:
                if not line.strip():
                    continue

                # Parse dmesg format: [timestamp] message
                timestamp = ""
                message = line
                match = re.match(r'\[(.*?)\]\s*(.*)', line)
                if match:
                    timestamp = match.group(1)
                    message = match.group(2)

                level = self._parse_log_level(message)

                # Extract source from message
                source = ""
                if ':' in message:
                    source = message.split(':')[0].split()[-1]

                entries.append(LogEntry(
                    timestamp=timestamp,
                    level=level,
                    source=source,
                    message=message,
                    raw=line
                ))

            return entries

        except FileNotFoundError:
            return [LogEntry(
                timestamp="",
                level=LogLevel.ERROR,
                source="",
                message="dmesg not found",
                raw="dmesg not available"
            )]
        except Exception as e:
            return [LogEntry(
                timestamp="",
                level=LogLevel.ERROR,
                source="",
                message=f"Error reading dmesg: {str(e)}",
                raw=f"Error: {str(e)}"
            )]

    def search_logs(self, pattern: str, log_path: Optional[str] = None,
                    use_regex: bool = False, case_sensitive: bool = False) -> List[LogEntry]:
        """Search logs for a pattern"""
        entries = []

        if log_path:
            entries = self.read_log_file(log_path, lines=1000)
        else:
            # Search syslog by default
            entries = self.read_journalctl(lines=500)

        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                regex = re.compile(pattern, flags)
                return [e for e in entries if regex.search(e.message)]
            except re.error:
                return []
        else:
            if case_sensitive:
                return [e for e in entries if pattern in e.message]
            else:
                pattern_lower = pattern.lower()
                return [e for e in entries if pattern_lower in e.message.lower()]

    def filter_by_level(self, entries: List[LogEntry], levels: List[LogLevel]) -> List[LogEntry]:
        """Filter log entries by level"""
        return [e for e in entries if e.level in levels]

    def filter_by_source(self, entries: List[LogEntry], sources: List[str]) -> List[LogEntry]:
        """Filter log entries by source"""
        return [e for e in entries if e.source in sources]

    def get_available_log_files(self) -> List[str]:
        """Get list of available log files"""
        available = []
        for name, path in self.default_log_paths.items():
            if os.path.exists(path):
                try:
                    # Check read permission
                    with open(path, 'r') as f:
                        f.read(1)
                    available.append(name)
                except (PermissionError, IOError):
                    pass
        return available

    def follow_log(self, log_path: Optional[str] = None,
                   callback: Optional[Callable[[LogEntry], None]] = None,
                   unit: Optional[str] = None) -> subprocess.Popen:
        """Follow a log file in real-time (returns a Popen object)"""
        if unit:
            cmd = ['journalctl', '-f', '-u', unit, '--no-pager']
        else:
            if log_path:
                cmd = ['tail', '-f', '-n', '50', log_path]
            else:
                cmd = ['journalctl', '-f', '--no-pager']

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        return process

    @staticmethod
    def format_level_color(level: LogLevel) -> str:
        """Get color code for log level (for UI)"""
        colors = {
            LogLevel.DEBUG: '9',      # Blue
            LogLevel.INFO: '8',       # White
            LogLevel.WARNING: '3',    # Yellow
            LogLevel.ERROR: '1',       # Red
            LogLevel.CRITICAL: '5',   # Magenta
            LogLevel.ALERT: '5',      # Magenta
            LogLevel.EMERGENCY: '5',  # Magenta
            LogLevel.UNKNOWN: '8',    # White
        }
        return colors.get(level, '8')

    def export_logs(self, entries: List[LogEntry], output_path: str,
                    format: str = 'text') -> tuple[bool, str]:
        """Export logs to a file"""
        try:
            if format == 'json':
                import json
                data = [
                    {
                        'timestamp': e.timestamp,
                        'level': e.level.value,
                        'source': e.source,
                        'message': e.message
                    }
                    for e in entries
                ]
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
            else:
                with open(output_path, 'w') as f:
                    for entry in entries:
                        f.write(entry.raw + '\n')

            return True, f"Logs exported to {output_path}"
        except Exception as e:
            return False, f"Failed to export logs: {str(e)}"
