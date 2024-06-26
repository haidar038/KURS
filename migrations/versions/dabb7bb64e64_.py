"""empty message

Revision ID: dabb7bb64e64
Revises: 758c1ad6d9df
Create Date: 2024-06-28 22:02:59.838639

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dabb7bb64e64'
down_revision = '758c1ad6d9df'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('artikel', schema=None) as batch_op:
        batch_op.add_column(sa.Column('thumbnail', sa.String(length=255), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('artikel', schema=None) as batch_op:
        batch_op.drop_column('thumbnail')

    # ### end Alembic commands ###
