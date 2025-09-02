"""add_api_key_hash_index

Revision ID: 2bb7a25865d5
Revises: 69bae4225f45
Create Date: 2025-09-02 18:59:46.386346

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2bb7a25865d5"
down_revision: Union[str, Sequence[str], None] = "69bae4225f45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_services_api_key_hash", "services", ["api_key_hash"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_services_api_key_hash", "services")
