"""empty message

Revision ID: 06912f2cc637
Revises: 9d356cd51db7
Create Date: 2020-04-30 22:10:36.066897

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '06912f2cc637'
down_revision = '9d356cd51db7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('post', sa.Column('meta_data', sa.PickleType(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('post', 'meta_data')
    # ### end Alembic commands ###
