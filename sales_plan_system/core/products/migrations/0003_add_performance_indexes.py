# Generated performance indexes migration for products

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    商品模块性能优化索引
    """

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        # ProductSKU 索引
        migrations.AddIndex(
            model_name='productsku',
            index=models.Index(
                fields=['status', 'created_at'],
                name='sku_status_created_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='productsku',
            index=models.Index(
                fields=['brand', 'status'],
                name='sku_brand_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='productsku',
            index=models.Index(
                fields=['category', 'status'],
                name='sku_category_status_idx'
            ),
        ),

        # Brand 索引
        migrations.AddIndex(
            model_name='brand',
            index=models.Index(
                fields=['is_active'],
                name='brand_active_idx'
            ),
        ),

        # Category 索引
        migrations.AddIndex(
            model_name='category',
            index=models.Index(
                fields=['parent', 'is_active'],
                name='category_parent_active_idx'
            ),
        ),
    ]
