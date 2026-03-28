from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('permissions', '0002_add_unique_constraints_to_userroleassignment'),
    ]

    operations = [
        migrations.RenameField(
            model_name='frontendpagepermission',
            old_name='allowed_roles',
            new_name='_legacy_allowed_roles',
        ),
        migrations.AlterField(
            model_name='frontendpagepermission',
            name='_legacy_allowed_roles',
            field=models.JSONField(blank=True, default=list, editable=False),
        ),
        migrations.AddField(
            model_name='frontendpagepermission',
            name='allowed_roles',
            field=models.ManyToManyField(blank=True, related_name='visible_pages', to='permissions.role'),
        ),
    ]
