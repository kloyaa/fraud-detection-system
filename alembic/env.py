"""Alembic environment configuration.

Handles database migrations with proper async support.
Reads SQLAlchemy URL from app.config.settings.
"""

from logging.config import fileConfig

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from alembic import context
from app.config import settings
from app.db.models import Base

# Load logging config
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use models' metadata for auto-migrations
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (without engine connection).

    This is useful for generating migration scripts statically.
    """
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with active database connection.

    Uses asyncpg for async I/O.
    """

    def process_revision_directives(context, revision, directives):
        """Auto-generate migration with downgrade path."""
        if config.cmd_opts and config.cmd_opts.autogenerate:
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []

    connectable = create_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
