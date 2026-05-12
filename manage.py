import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alembic.config import Config
from alembic import command


def main():
    import argparse

    parser = argparse.ArgumentParser(prog="manage.py", description="Laura Suite management commands")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("current", help="Show current migration")
    sub.add_parser("history", help="List migration history")
    migrate_p = sub.add_parser("migrate", help="Apply all pending migrations")
    migrate_p.add_argument("revision", nargs="?", default="head", help="Target revision")
    downgrade_p = sub.add_parser("downgrade", help="Rollback one migration")
    downgrade_p.add_argument("revision", nargs="?", default="-1", help="Target revision")
    makemigrate_p = sub.add_parser("make_migration", help="Create a new migration")
    makemigrate_p.add_argument("message", help="Migration message")
    makemigrate_p.add_argument("--autogenerate", action="store_true", default=True, help="Auto-detect changes")
    stamp_p = sub.add_parser("stamp", help="Stamp database with a revision")
    stamp_p.add_argument("revision", help="Revision to stamp")
    revision_p = sub.add_parser("revision", help="Create a blank migration")
    revision_p.add_argument("message", help="Revision message")

    args = parser.parse_args()

    alembic_cfg = Config("alembic.ini")

    if args.command == "current":
        command.current(alembic_cfg)
    elif args.command == "history":
        command.history(alembic_cfg)
    elif args.command == "migrate":
        command.upgrade(alembic_cfg, args.revision)
    elif args.command == "downgrade":
        command.downgrade(alembic_cfg, args.revision)
    elif args.command == "make_migration":
        command.revision(alembic_cfg, message=args.message, autogenerate=args.autogenerate)
    elif args.command == "stamp":
        command.stamp(alembic_cfg, args.revision)
    elif args.command == "revision":
        command.revision(alembic_cfg, message=args.message, autogenerate=False)


if __name__ == "__main__":
    main()
