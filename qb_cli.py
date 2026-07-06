#!/usr/bin/env python3
"""qb — direct QuickBooks terminal client.

Usage:
    qb_cli.py <Entity>                 Show the entity's schema (local file, no auth).
    qb_cli.py <Entity> "<WHERE clause>"  Run  SELECT * FROM <Entity> WHERE <clause>.

Reuses this repo's QuickBooksSession (Keychain-first OAuth) and
quickbooks_entity_schemas.json. This replaces the old shell helper, which piped
through `mcp-cli`/`claude --mcp-cli` — a path that broke when the Claude CLI
removed the `--mcp-cli` flag. Talking to QuickBooksSession directly needs no MCP
server spawn and no mcp-cli.
"""

import json
import sys
from pathlib import Path

SCHEMA_FILE = Path(__file__).parent / "quickbooks_entity_schemas.json"

USAGE = (
    "Usage: qb <Entity>                 (show schema)\n"
    "       qb <Entity> <WHERE clause>   (query)"
)


def show_schema(entity: str) -> int:
    try:
        schemas = json.loads(SCHEMA_FILE.read_text())
    except FileNotFoundError:
        print(f"Error: schema file not found: {SCHEMA_FILE}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: schema file is not valid JSON: {e}", file=sys.stderr)
        return 1

    schema = schemas.get(entity)
    if schema is None:
        available = ", ".join(sorted(schemas))
        print(
            f"Error: no schema for '{entity}'. Available entities: {available}",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(schema, indent=2))
    return 0


def _known_entities():
    """Entity names defined in the local schema file (empty set if unreadable)."""
    try:
        return set(json.loads(SCHEMA_FILE.read_text()).keys())
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def run_query(entity: str, where: str) -> int:
    # Validate the entity against the known schema so a caller can only target a
    # real QuickBooks entity (defense-in-depth; the entity is interpolated into
    # the query string). The WHERE clause is intentionally not restricted — the
    # QuickBooks query API is read-only (SELECT-only) and legitimate clauses use
    # quotes/%/LIKE, so char-filtering it would break normal queries.
    known = _known_entities()
    if known and entity not in known:
        print(
            f"Error: unknown entity '{entity}'. Known entities: {', '.join(sorted(known))}",
            file=sys.stderr,
        )
        return 1

    # Imported lazily so the schema path works even if credentials are absent.
    from quickbooks_interaction import QuickBooksSession

    try:
        session = QuickBooksSession()
    except Exception as e:
        print(f"Error: could not initialize QuickBooks session: {e}", file=sys.stderr)
        return 1

    query = f"SELECT * FROM {entity} WHERE {where}"
    try:
        result = session.query(query)
    except Exception as e:
        print(f"Error executing query: {e}", file=sys.stderr)
        return 1

    # QuickBooksSession.query returns a dict on success or an error string on
    # a non-200 response. Pretty-print dicts; surface error strings to stderr.
    if isinstance(result, (dict, list)):
        print(json.dumps(result, indent=2))
        return 0
    print(str(result), file=sys.stderr)
    return 1


def main(argv) -> int:
    if len(argv) < 2 or not argv[1].strip():
        print(USAGE, file=sys.stderr)
        return 1
    entity = argv[1]
    if len(argv) == 2:
        return show_schema(entity)
    where = " ".join(argv[2:])
    return run_query(entity, where)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
