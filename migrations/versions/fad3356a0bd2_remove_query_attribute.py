"""remove query attribute

Revision ID: fad3356a0bd2
Revises: f89f4ec22275
Create Date: 2023-07-18 18:03:44.644394

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fad3356a0bd2'
down_revision = 'f89f4ec22275'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_log', schema=None) as batch_op:
        batch_op.drop_column('query')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_log', schema=None) as batch_op:
        batch_op.add_column(sa.Column('query', sa.VARCHAR(length=200), nullable=True))

    # ### end Alembic commands ###
