"""Fail-closed local policy. Confirmation records come only from trusted code."""

from dataclasses import dataclass
import json
import math
from pathlib import Path
import time
from typing import Callable, Mapping


class PolicyError(ValueError):
    """The message is a stable, non-sensitive error code."""


@dataclass(frozen=True)
class Confirmation:
    subject: str
    role: str
    tool: str
    args_json: str
    expires_at: float


class Policy:
    """Opaque tokens must be unguessable and stored by the confirming server.

    No token issuance or write execution is provided. Even a valid confirmation
    cannot enable writes. The registry is local metadata, never model supplied.
    """

    def __init__(self, confirmations: Mapping[str, Confirmation] | None = None,
                 clock: Callable[[], float] = time.time):
        self._registry = json.loads(Path(__file__).with_name("registry.json").read_text())
        self._confirmations = confirmations if confirmations is not None else {}
        self._clock = clock

    def validate(self, name: str, args: dict, *, subject: str, role: str,
                 confirmation_token: str | None = None) -> dict:
        if type(name) is not str or name not in self._registry["tools"]:
            raise PolicyError("unknown_tool")
        spec = self._registry["tools"][name]
        if (type(spec.get("timeout_seconds")) not in (int, float)
                or not math.isfinite(spec["timeout_seconds"])
                or not 0 < spec["timeout_seconds"] <= 30
                or type(spec.get("max_output_bytes")) is not int
                or not 1 <= spec["max_output_bytes"] <= 1048576
                or spec.get("method") not in {"GET", "POST"}
                or type(spec.get("path")) is not str
                or not spec["path"].startswith("/api/")):
            raise PolicyError("invalid_spec")
        # All documented reads are parameterless. No guessed query parameters.
        if type(args) is not dict or args:
            raise PolicyError("invalid_args")
        if (type(subject) is not str or not subject.strip() or len(subject) > 256
                or type(role) is not str or role not in spec["roles"]):
            raise PolicyError("role_denied")
        if confirmation_token is not None:
            if (type(confirmation_token) is not str
                    or not 1 <= len(confirmation_token) <= 256):
                raise PolicyError("invalid_confirmation")
            record = self._confirmations.get(confirmation_token)
            if not isinstance(record, Confirmation):
                raise PolicyError("invalid_confirmation")
            if (type(record.expires_at) not in (int, float)
                    or not math.isfinite(record.expires_at)
                    or record.expires_at <= self._clock()):
                raise PolicyError("expired_confirmation")
            if (record.subject, record.role, record.tool, record.args_json) != (
                    subject, role, name, json.dumps(args, sort_keys=True, separators=(",", ":"))):
                raise PolicyError("invalid_confirmation")
        elif spec["confirmation_required"]:
            raise PolicyError("confirmation_required")
        if not spec["enabled"] or spec["kind"] != "read" or spec["method"] != "GET":
            raise PolicyError("write_disabled")
        return json.loads(json.dumps(spec))
