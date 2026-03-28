# Generated performance indexes migration

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    性能优化索引迁移

    为高频查询字段添加索引:
    - plan_month + status: 计划列表按月份和状态过滤
    - submitter + plan_month: 用户计划查询
    - submitted_at: 待审批列表排序
    """

    dependencies = [
        ('plans', '0003_plancampaign_plantask_plantaskitem'),
    ]

    operations = [
        # SalesPlan 索引
        migrations.AddIndex(
            model_name='salesplan',
            index=models.Index(
                fields=['plan_month', 'status'],
                name='salesplan_month_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='salesplan',
            index=models.Index(
                fields=['submitter', 'plan_month'],
                name='salesplan_submitter_month_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='salesplan',
            index=models.Index(
                fields=['status', 'submitted_at'],
                name='salesplan_status_submitted_idx'
            ),
        ),

        # SalesPlanItem 索引
        migrations.AddIndex(
            model_name='salesplanitem',
            index=models.Index(
                fields=['plan', 'target_month'],
                name='planitem_plan_month_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='salesplanitem',
            index=models.Index(
                fields=['sku', 'target_month'],
                name='planitem_sku_month_idx'
            ),
        ),

        # PlanCampaign 索引
        migrations.AddIndex(
            model_name='plancampaign',
            index=models.Index(
                fields=['plan_month', 'status'],
                name='campaign_month_status_idx'
            ),
        ),

        # PlanTask 索引
        migrations.AddIndex(
            model_name='plantask',
            index=models.Index(
                fields=['campaign', 'status'],
                name='task_campaign_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='plantask',
            index=models.Index(
                fields=['assignee', 'status'],
                name='task_assignee_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='plantask',
            index=models.Index(
                fields=['store', 'campaign'],
                name='task_store_campaign_idx'
            ),
        ),

        # PlanTaskItem 索引
        migrations.AddIndex(
            model_name='plantaskitem',
            index=models.Index(
                fields=['task', 'target_month'],
                name='taskitem_task_month_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='plantaskitem',
            index=models.Index(
                fields=['sku', 'target_month'],
                name='taskitem_sku_month_idx'
            ),
        ),
    ]
