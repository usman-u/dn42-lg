"""add column query to user_log table

Revision ID: f89f4ec22275
Revises: 0df9100a0b25
Create Date: 2023-07-18 16:26:38.620587

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f89f4ec22275'
down_revision = '0df9100a0b25'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_log', schema=None) as batch_op:
        batch_op.add_column(sa.Column('query', sa.String(length=200), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_log', schema=None) as batch_op:
        batch_op.drop_column('query')

    # ### end Alembic commands ###
