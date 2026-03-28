# Generated manually for phase-1 RBAC support.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('users', '0003_add_performance_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=100, unique=True)),
                ('module', models.CharField(max_length=50)),
                ('resource', models.CharField(max_length=50)),
                ('action', models.CharField(max_length=50)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'RBAC Permission',
                'verbose_name_plural': 'RBAC Permissions',
                'ordering': ['module', 'resource', 'action'],
            },
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('role_type', models.CharField(choices=[('system', 'System'), ('business', 'Business')], default='business', max_length=20)),
                ('description', models.TextField(blank=True)),
                ('priority', models.PositiveIntegerField(default=100)),
                ('is_system', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'RBAC Role',
                'verbose_name_plural': 'RBAC Roles',
                'ordering': ['priority', 'code'],
            },
        ),
        migrations.CreateModel(
            name='DataPermissionConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('subject_type', models.CharField(choices=[('user', 'User'), ('role', 'Role')], max_length=20)),
                ('target_roles', models.JSONField(blank=True, default=list)),
                ('scope_type', models.CharField(choices=[('all', 'All Stores'), ('org_unit', 'Org Unit'), ('store', 'Store')], default='store', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('org_units', models.ManyToManyField(blank=True, related_name='data_permission_configs', to='users.orgunit')),
                ('stores', models.ManyToManyField(blank=True, related_name='data_permission_configs', to='users.store')),
                ('target_users', models.ManyToManyField(blank=True, related_name='data_permission_configs', to='users.user')),
            ],
            options={
                'verbose_name': 'Data Permission Config',
                'verbose_name_plural': 'Data Permission Configs',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='DataScopeRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('resource_code', models.CharField(default='store', max_length=100)),
                ('subject_type', models.CharField(choices=[('user', 'User'), ('role', 'Role')], max_length=20)),
                ('scope_type', models.CharField(choices=[('all', 'All Stores'), ('org_unit', 'Org Unit'), ('store', 'Store'), ('self', 'Self-Owned'), ('subordinate', 'Subordinate-Owned'), ('assigned', 'Assigned')], default='store', max_length=20)),
                ('conditions', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('org_units', models.ManyToManyField(blank=True, related_name='data_scope_rules', to='users.orgunit')),
                ('stores', models.ManyToManyField(blank=True, related_name='data_scope_rules', to='users.store')),
                ('target_roles', models.ManyToManyField(blank=True, related_name='data_scope_rules', to='permissions.role')),
                ('target_users', models.ManyToManyField(blank=True, related_name='data_scope_rules', to='users.user')),
            ],
            options={
                'verbose_name': 'Data Scope Rule',
                'verbose_name_plural': 'Data Scope Rules',
                'ordering': ['resource_code', 'name'],
            },
        ),
        migrations.CreateModel(
            name='FrontendPagePermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_key', models.CharField(max_length=50, unique=True)),
                ('label', models.CharField(max_length=100)),
                ('url_name', models.CharField(blank=True, max_length=100)),
                ('permission_code', models.CharField(blank=True, max_length=100)),
                ('show_in_menu', models.BooleanField(default=True)),
                ('menu_order', models.PositiveIntegerField(default=100)),
                ('require_auth', models.BooleanField(default=True)),
                ('allow_all_users', models.BooleanField(default=False)),
                ('allowed_roles', models.JSONField(blank=True, default=list)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Frontend Page Permission',
                'verbose_name_plural': 'Frontend Page Permissions',
                'ordering': ['menu_order', 'page_key'],
            },
        ),
        migrations.CreateModel(
            name='RolePermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('effect', models.CharField(choices=[('allow', 'Allow'), ('deny', 'Deny')], default='allow', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('permission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_permissions', to='permissions.permission')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_permissions', to='permissions.role')),
            ],
            options={
                'verbose_name': 'Role Permission',
                'verbose_name_plural': 'Role Permissions',
                'ordering': ['role__priority', 'permission__code'],
                'unique_together': {('role', 'permission')},
            },
        ),
        migrations.CreateModel(
            name='UserRoleAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scope_type', models.CharField(choices=[('global', 'Global'), ('org_unit', 'Org Unit'), ('store', 'Store')], default='global', max_length=20)),
                ('starts_at', models.DateTimeField(blank=True, null=True)),
                ('ends_at', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('org_unit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='role_assignments', to='users.orgunit')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_assignments', to='permissions.role')),
                ('store', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='role_assignments', to='users.store')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_assignments', to='users.user')),
            ],
            options={
                'verbose_name': 'User Role Assignment',
                'verbose_name_plural': 'User Role Assignments',
                'ordering': ['user__username', 'role__priority', 'scope_type'],
            },
        ),
    ]
