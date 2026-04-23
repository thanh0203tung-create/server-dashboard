#!/usr/bin/env python3
"""
Terminal Server Dashboard - Ubuntu Server Management Tool
A beautiful TUI application for monitoring and managing Ubuntu servers.
"""

from app import ServerDashboardApp

def main():
    app = ServerDashboardApp()
    app.run()

if __name__ == "__main__":
    main()
