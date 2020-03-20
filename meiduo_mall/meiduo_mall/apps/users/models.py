# Create your models here.
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your views here.
from itsdangerous import TimedJSONWebSignatureSerializer, BadData


class User(AbstractUser):
    mobile = models.CharField(max_length=11,
                              unique=True,
                              verbose_name='phone')
    email_active = models.BooleanField(default=False,
                                       verbose_name='邮箱待验证')

    def generate_verify_email_url(self):
        """生成邮箱验证链接"""
        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY,
                                                     expires_in=60 * 60 * 24)

        data = {'user_id': self.id, 'email': self.email}
        token = serializer.dumps(data).decode()
        verify_url = settings.EMAIL_VERIFY_URL + token
        return verify_url

    @staticmethod
    def check_verify_email_token(token):
        """验证token并提取user"""
        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY,
                                                     expires_in=60 * 60 * 24)

        try:
            data = serializer.loads(token)
        except BadData:
            return None
        else:
            user_id = data.get('user_id')
            email = data.get('email')
        try:
            user = User.object.get(id=user_id,
                                   email=email)
        except User.DoesNotExist:
            return None
        else:
            return user

    class Meta:
        db_table = 'tb_users'
        verbose_name = 'user'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username
