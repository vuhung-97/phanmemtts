"""Shell giao diện SaaS: header, toolbar, sidebar, router, player."""

from __future__ import annotations

from ui.shell.app_header import AppHeader
from ui.shell.app_shell import AppShell
from ui.shell.app_toolbar import AppToolbar
from ui.shell.nav_sidebar import NavSidebar
from ui.shell.page import Page
from ui.shell.player_bar import PlayerBar

__all__ = ["AppHeader", "AppShell", "AppToolbar", "NavSidebar", "Page",
           "PlayerBar"]
