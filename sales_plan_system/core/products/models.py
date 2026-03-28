from django.db import models
from django.utils.translation import gettext_lazy as _


class Brand(models.Model):
    """品牌"""
    name = models.CharField('品牌名称', max_length=100, unique=True)
    code = models.CharField('品牌编码', max_length=50, unique=True)
    description = models.TextField('品牌描述', blank=True)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '品牌'
        verbose_name_plural = '品牌'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active'], name='brand_active_idx'),
        ]

    def __str__(self):
        return self.name


class Category(models.Model):
    """品类"""
    name = models.CharField('品类名称', max_length=100)
    code = models.CharField('品类编码', max_length=50, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                               verbose_name='上级品类', related_name='children')
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '品类'
        verbose_name_plural = '品类'
        ordering = ['code']
        indexes = [
            models.Index(fields=['parent', 'is_active'], name='category_parent_active_idx'),
        ]

    def __str__(self):
        return self.name


class ProductSKU(models.Model):
    """商品SKU"""

    class Status(models.TextChoices):
        ACTIVE = 'active', '在售'
        INACTIVE = 'inactive', '停售'
        OUT_OF_STOCK = 'out_of_stock', '缺货'

    sku_code = models.CharField('SKU编码', max_length=50, unique=True)
    sku_name = models.CharField('SKU名称', max_length=200)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name='品牌', related_name='skus')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name='品类', related_name='skus')
    spu_code = models.CharField('SPU编码', max_length=50, blank=True)
    spec_info = models.JSONField('规格信息', default=dict, blank=True,
                                 help_text='如: {"颜色": "红色", "容量": "50ml"}')
    unit = models.CharField('单位', max_length=20, default='件')
    unit_price = models.DecimalField('单价', max_digits=10, decimal_places=2, default=0)
    cost_price = models.DecimalField('成本价', max_digits=10, decimal_places=2, default=0)
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.ACTIVE)
    remark = models.TextField('备注', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '商品SKU'
        verbose_name_plural = '商品SKU'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at'], name='sku_status_created_idx'),
            models.Index(fields=['brand', 'status'], name='sku_brand_status_idx'),
            models.Index(fields=['category', 'status'], name='sku_category_status_idx'),
        ]

    def __str__(self):
        return f"[{self.sku_code}] {self.sku_name}"

    def get_spec_display(self):
        """获取规格显示文本"""
        if self.spec_info:
            return ' / '.join([f"{k}:{v}" for k, v in self.spec_info.items()])
        return '-'

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE
