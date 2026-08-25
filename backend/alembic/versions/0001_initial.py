"""initial schema from Development Pack 03_DATABASE_SCHEMA.md"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    from app.db import Base
    from app.models import *  # noqa: F401

    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    from app.db import Base

    Base.metadata.drop_all(bind=bind)
