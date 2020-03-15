import json
import re

from django_redis import get_redis_connection

from users.models import User
from django.views import View
from django.http import JsonResponse


class RegisterView(View):
    def post(self, request):
        dict = json.loads(request.body.decode())
        username = dict.get('username')
        password = dict.get('password')
        password2 = dict.get('password2')
        mobile = dict.get('mobile')
        allow = dict.get('allow')
        sms_code_client = dict.get('sms_code')

        if not all([username, password, password2, mobile, allow, sms_code_client]):
            return JsonResponse({'code': 400,
                                 'errmsg': '缺少必要参数'})

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return JsonResponse({'code': 400,
                                 'errmsg': 'username error'})

        if password != password2:
            return JsonResponse({'code': 400,
                                 'errmsg': '两次输入不一致'})

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({'code': 400,
                                 'errmsg': 'mobile error'})

        if allow != True:
            return JsonResponse({'code': 400,
                                 'errmsg': 'allow error'})

        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        if not sms_code_server:
            return JsonResponse({'code': 400,
                                 'reemsg': '短信验证码过期'})
        if sms_code_client != sms_code_server:
            return JsonResponse({'code': 400,
                                 'errmsg': '验证码错误'})

        try:
            user = User.objects.create_user(username=username,
                                            password=password,
                                            mobile=mobile)
        except Exception as error:
            return JsonResponse({'code': 400,
                                 'errmsg': '保存到数据库出错'})
        return JsonResponse({'code': 400,
                             'errmsg': 'OK'})


class UsernameCountView(View):
    def get(self, request, username):
        try:
            count = User.objects.filter(username=username).count()
        except Exception as e:
            return JsonResponse({'code': 400,
                                 'errmsg': 'sql_error'})
        return JsonResponse({'code': 0,
                             'errmsg': 'OK',
                             'count': count})


class MobileCountView(View):

    def get(self, request, mobile):
        count = User.objects.filter(mobile=mobile).count()
        return JsonResponse({'code': 0,
                             'errmsg': 'ok',
                             'count': count})
