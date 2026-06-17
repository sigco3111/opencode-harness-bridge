"""Exception hierarchy for opencode-harness-bridge.

All library exceptions inherit from :class:`OpenCodeHarnessBridgeError` so
users can catch everything with a single ``except`` clause.

Implementation note (for other-PC worker)
----------------------------------------
Keep this file dependency-free. Add new subclasses only when a *new class*
of error is possible (e.g. ``SecretLeakError`` is a *critical* subclass
that callers may want to handle differently from generic errors).
"""

from __future__ import annotations


class OpenCodeHarnessBridgeError(Exception):
    """Base class for all opencode-harness-bridge errors."""


class MigrationError(OpenCodeHarnessBridgeError):
    """Raised when a migration step fails. Chain the original via ``from``."""


class InvalidSourceError(OpenCodeHarnessBridgeError):
    """Raised when the source harness format is not recognized or unsupported."""


class InvalidTargetError(OpenCodeHarnessBridgeError):
    """Raised when the target harness format is not recognized or unsupported."""


class SecretLeakError(OpenCodeHarnessBridgeError):
    """Raised when a potential secret is detected in an asset that would be auto-applied.

    This is a *critical* safety error. Callers should treat any catch of this
    exception as a hard stop and require user review.
    """
