# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your views here.
class User(AbstractUser):
    mobile = models.CharField(max_length=11,
                              unique=True,
                              verbose_name='phone')

    class Meta:
        db_table = 'tb_users'
        verbose_name = 'user'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username
