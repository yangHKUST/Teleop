#!/usr/bin/env python3
"""Non-blocking raw-terminal keyboard reader, no third-party deps.

Reads single keystrokes from the controlling terminal (/dev/tty) in raw mode, so
it works even when the node's stdin is redirected -- e.g. launched in the
background from a script, where stdin becomes /dev/null (tcgetattr would fail
with ENOTTY). In raw mode the terminal emits one byte per keystroke, and
auto-repeat keeps emitting bytes while a key is held, so each returned entry is
one "step event" and holding a key yields continuous motion.

Ctrl-C raises KeyboardInterrupt (raw mode suppresses SIGINT), so callers can
still quit cleanly. The node is responsible for restoring the terminal via
stop() on exit and on SIGTERM/SIGINT.
"""

from __future__ import annotations

import os
import select
import sys
import termios
import tty
from typing import List, Optional


class KeyboardReader:
    def __init__(self, fd: Optional[int] = None) -> None:
        self._owns_fd = False
        if fd is not None:
            self._fd = fd
        else:
            # Prefer the controlling terminal so stdin redirection (e.g. a
            # backgrounded launch) doesn't break key capture.
            try:
                self._fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
                self._owns_fd = True
            except OSError:
                self._fd = sys.stdin.fileno()
        self._old: Optional[list] = None

    def __enter__(self) -> "KeyboardReader":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def start(self) -> None:
        if not os.isatty(self._fd):
            raise OSError(
                "no controlling terminal available; run keyboard_teleop from an "
                "interactive terminal"
            )
        self._old = termios.tcgetattr(self._fd)
        tty.setraw(self._fd)
        # raw 模式会清掉 OPOST, 使 '\n' 只换行不回行首, 打印会错位/缩进。
        # 恢复输出后处理(ONLCR), 让 print 照常 CRLF 顶格。
        attr = termios.tcgetattr(self._fd)
        attr[1] |= termios.OPOST | termios.ONLCR
        termios.tcsetattr(self._fd, termios.TCSANOW, attr)

    def stop(self) -> None:
        if self._old is not None:
            try:
                termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)
            except termios.error:
                pass
            self._old = None
        if self._owns_fd:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._owns_fd = False

    def read_keys(self) -> List[str]:
        """Drain all pending keystrokes; return decoded key names (lowercase)."""
        keys: List[str] = []
        while True:
            ready, _, _ = select.select([self._fd], [], [], 0.0)
            if not ready:
                break
            try:
                byte = os.read(self._fd, 1)
            except OSError:
                break
            if not byte:
                break
            key = self._decode(byte[0])
            if key is not None:
                keys.append(key)
        return keys

    def _decode(self, first: int) -> Optional[str]:
        if first == 0x03:              # Ctrl-C
            raise KeyboardInterrupt
        if first == 0x1B:              # Esc or escape-sequence lead-in
            if self._peek() is not None:   # arrow / F-key sequence -> swallow
                return None
            return "esc"
        if first == 0x7F:              # Backspace
            return "backspace"
        if first in (0x0A, 0x0D):      # Enter
            return "enter"
        if 0x20 <= first <= 0x7E:      # printable ASCII -> lowercase
            return chr(first).lower()
        return None

    def _peek(self) -> Optional[bytes]:
        ready, _, _ = select.select([self._fd], [], [], 0.0)
        if not ready:
            return None
        try:
            return os.read(self._fd, 16)
        except OSError:
            return None
