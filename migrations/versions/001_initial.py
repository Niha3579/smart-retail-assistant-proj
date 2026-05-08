"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.String(50), unique=True, nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('brand', sa.String(100)),
        sa.Column('category', sa.String(100)),
        sa.Column('subcategory', sa.String(100)),
        sa.Column('price', sa.Float(), default=0.0),
        sa.Column('currency', sa.String(10), default='INR'),
        sa.Column('discount_percent', sa.Float(), default=0.0),
        sa.Column('discounted_price', sa.Float(), default=0.0),
        sa.Column('rating', sa.Float(), default=0.0),
        sa.Column('reviews_count', sa.Integer(), default=0),
        sa.Column('popularity_score', sa.Float(), default=0.0),
        sa.Column('stock_status', sa.String(50), default='In Stock'),
        sa.Column('stock_quantity', sa.Integer(), default=100),
        sa.Column('date_added', sa.DateTime()),
        sa.Column('description', sa.Text()),
        sa.Column('image_url', sa.String(500)),
        sa.Column('is_active', sa.Boolean(), default=True),
    )
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('email', sa.String(200), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('is_admin', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_table(
        'carts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
    )
    op.create_table(
        'cart_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('cart_id', sa.Integer(), sa.ForeignKey('carts.id'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('quantity', sa.Integer(), default=1),
    )
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('customer_name', sa.String(150)),
        sa.Column('customer_email', sa.String(200)),
        sa.Column('shipping_address', sa.Text()),
        sa.Column('total_amount', sa.Float(), default=0.0),
        sa.Column('status', sa.String(50), default='Pending'),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('quantity', sa.Integer(), default=1),
        sa.Column('unit_price', sa.Float(), default=0.0),
    )
    op.create_table(
        'sales_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('date', sa.Date()),
        sa.Column('product_id', sa.String(50)),
        sa.Column('product_name', sa.String(200)),
        sa.Column('category', sa.String(100)),
        sa.Column('units_sold', sa.Integer(), default=0),
        sa.Column('revenue', sa.Float(), default=0.0),
        sa.Column('region', sa.String(100)),
        sa.Column('channel', sa.String(100)),
        sa.Column('created_at', sa.DateTime()),
    )


def downgrade():
    op.drop_table('sales_records')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('cart_items')
    op.drop_table('carts')
    op.drop_table('users')
    op.drop_table('products')
