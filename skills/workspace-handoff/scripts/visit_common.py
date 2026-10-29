#!/usr/bin/env python3
"""Shared helpers for a nurse visit script.

MCP tools are callable only from execute_command with
execution_type mcp_orchestration, via hai_mcp.call_mcp.
call_mcp returns {success, result}. result is a list. result[0] is
the tool dict or a JSON string of that dict. result[1], when present,
is ignored. The tool dict uses ok, not success.
"""
import json
import sys
import time
from pathlib import Path


class Budget:
    """Wall clock for one orchestration run. The MCP token lasts 5 minutes."""

    def __init__(self, seconds=240):
        self.deadline = time.monotonic() + seconds

    def left(self):
        return self.deadline - time.monotonic()

    def exhausted(self):
        return self.left() <= 0


def mcp_call(tool, args, retries=1):
    """Call one attached MCP tool. Returns the raw envelope.

    ImportError means this process is not mcp_orchestration. A raise
    from call_mcp is a failed envelope, not a traceback. Tool-not-found
    is not retried. One retry when the envelope says success false.
    Never reads or prints the environment.
    """
    try:
        from hai_mcp import call_mcp
    except ImportError:
        print(
            '{"error": "hai_mcp unavailable; run with execution_type mcp_orchestration"}',
            file=sys.stderr,
        )
        sys.exit(1)
    last = None
    for attempt in range(retries + 1):
        try:
            last = call_mcp(tool, args)
        except Exception as exc:
            text = str(exc).split("Available tools:")[0].strip()
            last = {"success": False, "error": text[:200] or "call_mcp raised"}
            if "not found" in text.lower():
                return last
        if isinstance(last, dict) and last.get("success"):
            return last
        if attempt < retries:
            continue
    return last if isinstance(last, dict) else {"success": False, "error": "empty envelope"}


def tool_dict(envelope):
    """Return (tool dict, error) from a hai_mcp envelope.

    A bare tool dict is accepted. ok false is an error. A missing ok
    is still the tool body.
    """
    if not isinstance(envelope, dict):
        return None, "envelope not an object"
    if "ok" in envelope and "success" not in envelope:
        inner = envelope
    else:
        if not envelope.get("success"):
            err = envelope.get("error")
            return None, str(err or "success false")[:200]
        outer = envelope.get("result")
        raw = outer[0] if isinstance(outer, list) and outer else outer
        if raw is None:
            return None, "empty result"
        if isinstance(raw, str):
            try:
                raw = json.loads(raw, strict=False)
            except json.JSONDecodeError:
                return None, "result[0] not json"
        if not isinstance(raw, dict):
            return None, "inner envelope not an object"
        inner = raw
    if inner.get("ok") is False:
        return None, str(inner.get("error") or "ok false")[:200]
    return inner, None


def load_json(ws, rel):
    path = Path(ws) / rel
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate(instance, schema_path):
    """Raise ValueError with the first schema errors. jsonschema is preinstalled."""
    import jsonschema

    with open(schema_path, encoding="utf-8") as fh:
        schema = json.load(fh)
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        lines = []
        for err in errors[:8]:
            where = "/".join(str(p) for p in err.path) or "(root)"
            lines.append(f"{where}: {err.message}")
        raise ValueError("; ".join(lines))


def summary(payload):
    """One JSON line. The nurse reads the last stdout line, so print this last."""
    line = json.dumps(payload, separators=(",", ":"), default=str)
    if len(line.encode("utf-8")) > 2048:
        line = json.dumps(
            {
                "plane": payload.get("plane"),
                "status": payload.get("status"),
                "error": "summary too long",
            },
            separators=(",", ":"),
        )
    return line
