"""Utility to migrate legacy JSON data into the PostgreSQL database."""

from __future__ import annotations


def main() -> None:
    """Execute migration from JSON files to the relational schema idempotently."""
    # TODO: Implement UPSERT-based migration with journaling per roadmap.
    raise NotImplementedError("migrate_json_to_db script not implemented yet")


if __name__ == "__main__":
    main()
