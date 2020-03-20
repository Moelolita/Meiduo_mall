import json
import re
from django.views import View
from django.http import JsonResponse
from django.contrib.auth import login, authenticate, logout
from django_redis import get_redis_connection
from meiduo_mall.utils.view import LoginRequiredMixin
from users.models import User
import logging

logger = logging.getLogger('django')


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
        login(request, user)

        response = JsonResponse({'code': 400,
                                 'errmsg': 'OK'})
        response.set_cookie('username', user.username, max_age=3600 * 24 * 14)
        return response


class LoginView(View):
    def post(self, request):
        """用户登录"""
        # 接收前端参数
        dict = json.loads(request.body.decode())
        username = dict.get('username')
        password = dict.get('password')
        remembered = dict.get('remembered')
        # 整体校验
        if not all([username, password]):
            return JsonResponse({'code': 400,
                                 'errmsg': '缺少必传参数'})
        # 与数据库对比
        user = authenticate(username=username,
                            password=password)

        if not user:
            return JsonResponse({'code': 400,
                                 'errmsg': '用户名或密码错误'})
        # 状态保持
        login(request, user)
        # 是否记住登录
        if not remembered:
            request.session.set_expiry(0)
        else:
            request.session.set_expiry(None)

        response = JsonResponse({'code': 400,
                                 'errmsg': 'OK'})
        response.set_cookie('username', user.username, max_age=3600 * 24 * 14)
        return response


class LoginoutView(View):
    """退出登录"""

    def delete(self, request):
        logout(request)
        response = JsonResponse({'code': 0,
                                 'errmsg': 'OK'})
        response.delete_cookie('username')
        return response


class UserInfoView(LoginRequiredMixin, View):
    """用户中心"""

    def get(self, request):
        info_data = {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        }

        return JsonResponse({'code': 0,
                             'errmsg': 'OK',
                             'info_data': info_data})


class EmailView(View):
    """添加邮箱"""

    def put(self, request):
        json_dict = json.loads(request.body.decode())
        email = json_dict.get('email')

        if not email:
            return JsonResponse({'code': 400,
                                 'errmsg': '缺少email参数'})

        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return JsonResponse({'code': 400,
                                 'errmsg': '参数email有误'})

        try:
            request.user.email = email
            request.user.save()
        except Exception as error:
            logger.error(error)
            return JsonResponse({'code': 400,
                                 'errmsg': '添加邮箱失败'})

        from celery_tasks.email.tasks import send_verify_email
        verify_url = request.user.generate_verify_email_url()
        send_verify_email.delay(email, verify_url)

        return JsonResponse({'code': 0,
                             'errmsg': 'ok'})


class VerifyEmailView(View):
    """验证邮箱"""

    def put(self, request):
        token = request.GET.get('token')
        if not token:
            return JsonResponse({'code': 400,
                                 'errmsg': '缺少token'})
        user = User.check_verify_email_token(token)
        if not user:
            return JsonResponse({'code': 400,
                                 'errmsg': '无效的token'})
        try:
            user.email_active = True
            user.save()
        except Exception as error:
            logger.error(error)
            return JsonResponse({'code': 400,
                                 'errmsg': '激活邮件失败'})
        return JsonResponse({'code': 0,
                             'errmsg': 'ok'})


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
