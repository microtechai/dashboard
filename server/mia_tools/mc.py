"""Fixed-origin MC adapter using a trusted, injectable, session-scoped transport.

No default HTTP client is installed. Transport implementations MUST honor the
total timeout (including body reads), cap reads at max_bytes, reject redirects,
and attach only the authenticated caller's MC credentials. Python cannot forcibly
cancel arbitrary injected code; late returns are rejected as an extra check.
Responses are untrusted JSON data, never instructions or executable model text.
"""

from dataclasses import dataclass
import json
import math
import time
from typing import Protocol

from .policy import Policy, PolicyError

MC_ORIGIN = "http://127.0.0.1:9090"
MAX_TIMEOUT = 5.0
MAX_OUTPUT_BYTES = 65536


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes


class Transport(Protocol):
    def __call__(self, *, method: str, url: str, timeout: float,
                 max_bytes: int) -> Response: ...


class MCAdapter:
    def __init__(self, transport: Transport | None = None, *,
                 policy: Policy | None = None, timeout: float = MAX_TIMEOUT,
                 max_output_bytes: int = MAX_OUTPUT_BYTES):
        if (type(timeout) not in (int, float) or not math.isfinite(timeout)
                or not 0 < timeout <= MAX_TIMEOUT):
            raise ValueError("invalid_timeout")
        if type(max_output_bytes) is not int or not 1 <= max_output_bytes <= MAX_OUTPUT_BYTES:
            raise ValueError("invalid_output_limit")
        self._transport = transport
        self._policy = policy if policy is not None else Policy()
        self._timeout = timeout
        self._max_bytes = max_output_bytes

    def call(self, name: str, args: dict, *, subject: str, role: str,
             confirmation_token: str | None = None) -> dict:
        result = {"ok": False, "source_url": None, "status": None,
                  "data": None, "error": None}
        try:
            spec = self._policy.validate(name, args, subject=subject, role=role,
                                         confirmation_token=confirmation_token)
        except PolicyError as exc:
            result["error"] = str(exc)
            return result
        result["source_url"] = MC_ORIGIN + spec["path"]
        if self._transport is None:
            result["error"] = "transport_unavailable"
            return result
        timeout = min(self._timeout, spec["timeout_seconds"])
        limit = min(self._max_bytes, spec["max_output_bytes"])
        started = time.monotonic()
        try:
            response = self._transport(method="GET", url=result["source_url"],
                                       timeout=timeout, max_bytes=limit + 1)
            if (not isinstance(response, Response) or type(response.status) is not int
                    or not 100 <= response.status <= 599):
                result["error"] = "invalid_response"
                return result
            result["status"] = response.status
            if time.monotonic() - started >= timeout:
                raise TimeoutError
            if type(response.body) is not bytes:
                result["error"] = "invalid_response"
            elif len(response.body) > limit:
                result["error"] = "output_limit"
            elif 300 <= response.status < 400:
                result["error"] = "redirect_not_allowed"
            elif not 200 <= response.status < 300:
                result["error"] = "http_error"
            else:
                data = json.loads(response.body.decode("utf-8"),
                                  parse_constant=_reject_constant)
                # Bound the serialized data too (escaping/spacing can expand it).
                if len(json.dumps(data, ensure_ascii=True, allow_nan=False).encode("utf-8")) > limit:
                    result["error"] = "output_limit"
                else:
                    result.update(ok=True, data=data)
        except TimeoutError:
            result["error"] = "timeout"
        except (ValueError, UnicodeError, RecursionError):
            result["error"] = "invalid_response"
        except Exception:
            # Never expose transport exception text, credentials or upstream bodies.
            result["error"] = "transport_error"
        return result


def _reject_constant(value: str):
    raise ValueError("non_finite_json")
