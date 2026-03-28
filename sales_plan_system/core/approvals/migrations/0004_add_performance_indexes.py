# Generated performance indexes migration for approvals

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    审批模块性能优化索引
    """

    dependencies = [
        ('approvals', '0003_taskapprovalrecord'),
    ]

    operations = [
        # ApprovalRecord 索引
        migrations.AddIndex(
            model_name='approvalrecord',
            index=models.Index(
                fields=['plan', 'approval_level'],
                name='approval_plan_level_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='approvalrecord',
            index=models.Index(
                fields=['approver', 'created_at'],
                name='approval_approver_time_idx'
            ),
        ),

        # TaskApprovalRecord 索引
        migrations.AddIndex(
            model_name='taskapprovalrecord',
            index=models.Index(
                fields=['task', 'approval_level'],
                name='taskapproval_task_level_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='taskapprovalrecord',
            index=models.Index(
                fields=['approver', 'created_at'],
                name='taskapproval_approver_time_idx'
            ),
        ),

        # ApprovalFlow 索引
        migrations.AddIndex(
            model_name='approvalflow',
            index=models.Index(
                fields=['flow_type', 'is_active'],
                name='approvalflow_type_active_idx'
            ),
        ),
    ]
