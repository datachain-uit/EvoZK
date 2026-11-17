"""Exceptions raised by the analyser. All are ValueErrors: bad input never produces an output."""


class AnalyserError(ValueError):
    """Base class."""


class InventoryError(AnalyserError):
    """A path inventory is malformed (missing keys, bounds that do not match the path, duplicates)."""


class PolicyError(AnalyserError):
    """The statement policy does not fit the inventories (unknown path, duplicate field, inconsistent rename)."""


class StateError(AnalyserError):
    """The A0-pad state (K, exhaustion count) is inconsistent with the old version."""
