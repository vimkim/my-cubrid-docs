#!/usr/bin/env python3
from dataclasses import dataclass


@dataclass
class Request:
    state: str = "IDLE"
    dirty: bool = True
    flushing: bool = False
    frozen: bool = False
    io_ref: int = 0
    terminal_owner: bool = False
    wakeups: int = 0

    def prepare(self) -> None:
        assert self.state == "IDLE" and self.dirty
        self.state = "PREPARING"
        self.flushing = True
        self.frozen = True
        self.io_ref = 1

    def submitted(self) -> None:
        assert self.state == "PREPARING"
        self.state = "SUBMITTED"

    def complete(self, result: str) -> bool:
        if self.terminal_owner:
            return False
        assert self.state in {"PREPARING", "SUBMITTED"}
        self.terminal_owner = True
        self.state = "COMPLETING"
        if result == "SUCCESS":
            self.dirty = False
        else:
            self.dirty = True
        self.flushing = False
        self.frozen = False
        self.io_ref = 0
        self.wakeups += 1
        self.state = "IDLE"
        return True


def observe(name: str, result: str, duplicate: bool = False) -> None:
    req = Request()
    req.prepare()
    if result != "SUBMIT_FAILED":
        req.submitted()
    first = req.complete(result)
    second = req.complete(result) if duplicate else None
    assert req.state == "IDLE"
    assert not req.flushing and not req.frozen and req.io_ref == 0
    assert req.wakeups == 1
    print(name, result, "first_owner=", first, "second_owner=", second,
          "dirty=", req.dirty, "cleanup=OK")


observe("normal", "SUCCESS")
observe("submit", "SUBMIT_FAILED")
observe("io", "IO_ERROR")
observe("cancel", "CANCELLED")
observe("duplicate", "SUCCESS", duplicate=True)
