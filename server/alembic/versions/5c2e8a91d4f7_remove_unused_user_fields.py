"""remove unused user fields

Onboarding collected language, purpose and date of birth, and Settings stored
an email-notifications preference, but nothing in the app ever used them, so
the features and their data are gone.

Revision ID: 5c2e8a91d4f7
Revises: 1ed10c6b3640
Create Date: 2026-10-12 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c2e8a91d4f7'
down_revision: Union[str, Sequence[str], None] = '1ed10c6b3640'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('users', 'language')
    op.drop_column('users', 'purpose')
    op.drop_column('users', 'date_of_birth')
    op.drop_column('users', 'is_onboarded')
    op.drop_column('users', 'email_notifications')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('users', sa.Column('email_notifications', sa.BOOLEAN(), server_default=sa.false(), nullable=False))
    # Existing users count as onboarded, so a rollback doesn't send them
    # through the old onboarding screen.
    op.add_column('users', sa.Column('is_onboarded', sa.BOOLEAN(), server_default=sa.true(), nullable=False))
    op.add_column('users', sa.Column('date_of_birth', sa.DATE(), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('purpose', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('language', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
