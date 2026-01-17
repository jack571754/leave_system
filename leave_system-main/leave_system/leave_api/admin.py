from django.contrib import admin
from .models import LeaveRequest


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'staff_full_name', 'user_email', 'reason_short', 'leave_hours', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user_email', 'staff_full_name', 'reason']
    readonly_fields = ['process_instance_id', 'process_model_id', 'created_at', 'updated_at', 'submitted_at']
    
    def reason_short(self, obj):
        return obj.reason[:30] + '...' if len(obj.reason) > 30 else obj.reason
    reason_short.short_description = '请假原因'

