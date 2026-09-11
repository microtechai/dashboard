"""Private, standalone MC reads; no chat integration or import-time network I/O.

The caller must authenticate the session before each call and derive identity and
local role server-side. Never accept identity, role or transport from model text.
"""

from .mc import MCAdapter, Response
from .policy import Confirmation, Policy, PolicyError

__all__ = ["MCAdapter", "Response", "Confirmation", "Policy", "PolicyError"]
