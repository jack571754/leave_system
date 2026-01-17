"""
组织架构数据模型
定义部门、员工、角色等组织架构相关模型
"""

from django.db import models
from django.contrib.auth.models import User


class Department(models.Model):
    """
    部门模型
    支持树形结构，可以有父部门和子部门
    """
    name = models.CharField(
        max_length=100,
        verbose_name='部门名称',
        help_text='部门的名称'
    )
    
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name='父部门',
        help_text='上级部门，支持树形结构'
    )
    
    manager = models.ForeignKey(
        'Employee',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='managed_departments',
        verbose_name='部门负责人',
        help_text='该部门的负责人'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    class Meta:
        verbose_name = '部门'
        verbose_name_plural = '部门'
        ordering = ['name']
        indexes = [
            models.Index(fields=['parent']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_full_path(self):
        """获取部门的完整路径"""
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name


class Employee(models.Model):
    """
    员工模型
    关联 Django User，存储员工的组织架构信息
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name='用户账号',
        help_text='关联的 Django 用户账号'
    )
    
    employee_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='员工工号',
        help_text='员工的唯一工号'
    )
    
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='employees',
        verbose_name='所属部门',
        help_text='员工所属的部门'
    )
    
    position = models.CharField(
        max_length=100,
        verbose_name='职位',
        help_text='员工的职位名称'
    )
    
    level = models.IntegerField(
        verbose_name='职级',
        help_text='员工的职级，1-10，数字越大职级越高'
    )
    
    direct_manager = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='subordinates',
        verbose_name='直属上级',
        help_text='员工的直属上级'
    )
    
    email = models.EmailField(
        verbose_name='邮箱',
        help_text='员工的邮箱地址'
    )
    
    phone = models.CharField(
        max_length=20,
        verbose_name='电话',
        help_text='员工的联系电话'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    class Meta:
        verbose_name = '员工'
        verbose_name_plural = '员工'
        ordering = ['employee_id']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['department']),
            models.Index(fields=['direct_manager']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name() or self.user.username}"
    
    def get_full_name(self):
        """获取员工全名"""
        return self.user.get_full_name() or self.user.username


class Role(models.Model):
    """
    角色模型
    定义系统中的各种角色，如 HR、财务、部门主管等
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='角色名称',
        help_text='角色的唯一名称'
    )
    
    description = models.TextField(
        verbose_name='角色描述',
        help_text='角色的详细描述'
    )
    
    employees = models.ManyToManyField(
        Employee,
        related_name='roles',
        verbose_name='角色成员',
        help_text='拥有该角色的员工'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    class Meta:
        verbose_name = '角色'
        verbose_name_plural = '角色'
        ordering = ['name']
    
    def __str__(self):
        return self.name
