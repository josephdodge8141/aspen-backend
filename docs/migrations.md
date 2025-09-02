# Database Migrations

This document describes how to create, review, and run database migrations in the Aspen Backend project.

## Overview

We use [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations. Alembic is integrated with SQLModel to automatically detect changes to our model definitions and generate migration scripts.

## Migration Workflow

### 1. Making Model Changes

When you modify any SQLModel classes in `app/models/`, you need to create a migration:

1. Make your changes to the model files
2. Generate a new migration
3. Review the generated migration
4. Apply the migration
5. Test the changes

### 2. Generating Migrations

```bash
# Generate a new migration with auto-detected changes
docker compose exec app alembic revision --autogenerate -m "descriptive_message"

# Generate an empty migration (for data migrations or complex changes)
docker compose exec app alembic revision -m "descriptive_message"
```

### 3. Applying Migrations

```bash
# Apply all pending migrations
docker compose exec app alembic upgrade head

# Apply migrations to a specific revision
docker compose exec app alembic upgrade <revision_id>

# Downgrade to a previous revision
docker compose exec app alembic downgrade <revision_id>
```

### 4. Checking Migration Status

```bash
# Show current migration status
docker compose exec app alembic current

# Show migration history
docker compose exec app alembic history

# Show pending migrations
docker compose exec app alembic heads
```

## Naming Convention

Migration files should follow this naming pattern:
```
YYYYMMDDHHMM_<short_description>.py
```

Examples:
- `202501021430_create_user_tables.py`
- `202501031200_add_user_preferences.py`
- `202501041500_index_optimization.py`

**Note**: Alembic automatically generates timestamps, but you should ensure the description is clear and concise.

## Migration File Structure

A typical migration file looks like this:

```python
"""create_user_tables

Revision ID: a1b2c3d4e5f6
Revises: f6e5d4c3b2a1
Create Date: 2025-01-02 14:30:00.123456

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel  # Add this for SQLModel types

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f6e5d4c3b2a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # Migration code here
    pass

def downgrade() -> None:
    """Downgrade schema."""
    # Rollback code here
    pass
```

## Best Practices

### 1. Review Generated Migrations

Always review auto-generated migrations before applying them:

- Check that column types are correct
- Verify foreign key constraints
- Ensure indexes are properly created
- Review any data transformations

### 2. Test Migrations

Before committing a migration:

```bash
# Test upgrade
docker compose exec app alembic upgrade head

# Test downgrade (if applicable)
docker compose exec app alembic downgrade -1

# Re-apply to ensure it works
docker compose exec app alembic upgrade head
```

### 3. Handle Data Migrations

For complex data migrations, create custom migration functions:

```python
def upgrade() -> None:
    # Schema changes first
    op.add_column('users', sa.Column('full_name', sa.String(255)))
    
    # Data migration
    connection = op.get_bind()
    connection.execute(
        "UPDATE users SET full_name = first_name || ' ' || last_name"
    )
    
    # Remove old columns if needed
    op.drop_column('users', 'first_name')
    op.drop_column('users', 'last_name')
```

### 4. Handle Breaking Changes

For backwards-incompatible changes:

1. **Add new column/table** (migration 1)
2. **Migrate data** (migration 2)
3. **Remove old column/table** (migration 3)

This allows for zero-downtime deployments.

### 5. SQLModel Integration

When working with SQLModel types, always add the import:

```python
import sqlmodel
```

This ensures that SQLModel-specific types (like `AutoString`) are properly handled.

## Common Migration Patterns

### Adding a New Table

```python
def upgrade() -> None:
    op.create_table('new_table',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_on', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
```

### Adding an Index

```python
def upgrade() -> None:
    op.create_index('idx_users_email', 'users', ['email'])

def downgrade() -> None:
    op.drop_index('idx_users_email', table_name='users')
```

### Adding a Foreign Key

```python
def upgrade() -> None:
    op.add_column('posts', sa.Column('author_id', sa.Integer()))
    op.create_foreign_key('fk_posts_author', 'posts', 'users', ['author_id'], ['id'])

def downgrade() -> None:
    op.drop_constraint('fk_posts_author', 'posts', type_='foreignkey')
    op.drop_column('posts', 'author_id')
```

### Renaming a Column

```python
def upgrade() -> None:
    op.alter_column('users', 'old_name', new_column_name='new_name')

def downgrade() -> None:
    op.alter_column('users', 'new_name', new_column_name='old_name')
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all model imports are in `alembic/env.py`
2. **Type Errors**: Add `import sqlmodel` to migration files
3. **Circular Dependencies**: Handle with careful FK creation order
4. **Data Loss**: Always backup production data before major migrations

### Recovery Commands

```bash
# Reset to a specific revision (DANGER: data loss)
docker compose exec app alembic downgrade <revision_id>

# Mark current state without running migrations
docker compose exec app alembic stamp <revision_id>

# Generate SQL without executing
docker compose exec app alembic upgrade head --sql
```

## Environment-Specific Considerations

### Development
- Feel free to squash/modify migrations during development
- Reset database when needed: `docker compose down -v && docker compose up`

### Staging/Production
- **Never modify existing migrations** that have been applied
- **Always test migrations** on staging first
- **Backup database** before applying migrations
- Consider **maintenance windows** for large migrations

## CI/CD Integration

Migrations are automatically tested in CI:

```yaml
# .github/workflows/ci.yml
- name: Run migrations
  run: docker compose exec app alembic upgrade head
```

This ensures all migrations can be applied cleanly from an empty database.

## Monitoring

After applying migrations in production:

1. **Check application logs** for errors
2. **Monitor database performance** for slow queries
3. **Verify data integrity** with spot checks
4. **Monitor disk space** for large table changes

## Support

For migration issues:
1. Check this documentation
2. Review Alembic documentation
3. Ask the team for help
4. Consider reverting and creating a new migration

---

**Remember**: Migrations are permanent once applied to production. Take time to review and test thoroughly! 