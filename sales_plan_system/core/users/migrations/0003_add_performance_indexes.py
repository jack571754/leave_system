# Generated performance indexes migration for users

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    用户模块性能优化索引
    """

    dependencies = [
        ('users', '0002_orgunit_store_user_org_unit_storemembership'),
    ]

    operations = [
        # User 索引
        migrations.AddIndex(
            model_name='user',
            index=models.Index(
                fields=['role', 'is_active'],
                name='user_role_active_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(
                fields=['department', 'is_active'],
                name='user_dept_active_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(
                fields=['manager'],
                name='user_manager_idx'
            ),
        ),

        # Department 索引
        migrations.AddIndex(
            model_name='department',
            index=models.Index(
                fields=['is_active'],
                name='dept_active_idx'
            ),
        ),

        # OrgUnit 索引
        migrations.AddIndex(
            model_name='orgunit',
            index=models.Index(
                fields=['unit_type', 'is_active'],
                name='orgunit_type_active_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='orgunit',
            index=models.Index(
                fields=['parent'],
                name='orgunit_parent_idx'
            ),
        ),

        # Store 索引
        migrations.AddIndex(
            model_name='store',
            index=models.Index(
                fields=['org_unit', 'is_active'],
                name='store_orgunit_active_idx'
            ),
        ),

        # StoreMembership 索引
        migrations.AddIndex(
            model_name='storemembership',
            index=models.Index(
                fields=['user', 'is_active'],
                name='storemember_user_active_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='storemembership',
            index=models.Index(
                fields=['store', 'role', 'is_active'],
                name='storemember_store_role_idx'
            ),
        ),
    ]
