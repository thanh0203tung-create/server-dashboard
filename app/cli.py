#!/usr/bin/env python3
"""
CLI Entry Point for vipe-server-dashboard
"""

import sys
from app.ui.dashboard import ServerDashboardApp

def main():
    app = ServerDashboardApp()
    app.run()

if __name__ == "__main__":
    main()
