from django.db import models


# Create your models here.
class Area(models.Model):
    """区域划分"""
    name = models.CharField(max_length=20,
                            verbose_name='名称')
    parent = models.ForeignKey('self',
                               on_delete=models.SET_NULL,
                               related_name='subs',
                               null=True,
                               blank=True,
                               verbose_name='上级区域')

    class Meta:
        db_table = 'tb_areas'
        verbose_name = '行政区域'
        verbose_name_plural = '行政区域'

    def __str__(self):
        return self.name
