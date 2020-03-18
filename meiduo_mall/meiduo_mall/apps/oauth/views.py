from django.shortcuts import render

# Create your views here.
import json
import re
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.contrib.auth import login
from django_redis import get_redis_connection
from QQLoginTool.QQtool import OAuthQQ
from users.models import User
from .utils import generate_access_token
from .utils import check_access_token
from .models import OAuthQQUser
import logging

logger = logging.getLogger('django')


class QQURLView(View):
    def get(self, request):
        next = request.GET.get('next')
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI,
                        state=next)
        login_url = oauth.get_qq_url()
        return JsonResponse({'code': 0,
                             'errmsg': 'OK',
                             'login_url': login_url})


class QQUserView(View):
    def get(self, request):
        code = request.GET.get('code')
        if not code:
            return JsonResponse({'code': 400,
                                 'errmsg': '缺少code参数'})

        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI)

        try:
            access_token = oauth.get_access_token(code)
            openid = oauth.get_open_id(access_token)

        except Exception as error:
            logger.error(error)
            return JsonResponse({'code': 400,
                                 'errmsg': 'oauth2.0认证失败, 即获取qq信息失败'})

        try:
            oauth_qq = OAuthQQUser.objects.get(openid=openid)

        except OAuthQQUser.DoesNotExist:
            access_token = generate_access_token(openid)
            return JsonResponse({'code': 300,
                                 'errmsg': 'OK',
                                 'access_token': access_token})

        else:
            user = oauth_qq.user
            login(request, user)
            response = JsonResponse({'code': 0,
                                     'errmsg': 'OK'})
            response.set_cookie('username', user.username, max_age=3600 * 24 * 14)
            return response

    def post(self, request):
        dict = json.load(request.body.decode())
        mobile = dict.get('mobile')
        password = dict.get('password')
        sms_code_client = dict.get('sms_code')
        access_token = dict.get('access_token')

        if not all([mobile, password, sms_code_client]):
            return JsonResponse({'code': 400,
                                 'errmsg': '缺少必传参数'})

        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({'code': 400,
                                 'errmsg': '请输入正确的手机号码'})

        # 判断密码是否合格
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return JsonResponse({'code': 400,
                                 'errmsg': '请输入8-20位的密码'})

        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get('sms_%s' % mobile)

        if not sms_code_server:
            return JsonResponse({'code': 400,
                                 'errmsg': '验证码失效'})
        # 如果有, 则进行判断:
        if sms_code_client != sms_code_server.decode():
            # 如果不匹配, 则直接返回:
            return JsonResponse({'code': 400,
                                 'errmsg': '输入的验证码有误'})
        openid = check_access_token(access_token)
        if not openid:
            return JsonResponse({'code': 400,
                                 'errmsg': '缺少openid'})
        # 保存注册数据
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 用户不存在,新建用户
            user = User.objects.create_user(username=mobile,
                                            password=password,
                                            mobile=mobile)
        else:
            # 如果用户存在，检查用户密码
            if not user.check_password(password):
                return JsonResponse({'code': 400,
                                     'errmsg': '输入的密码不正确'})
        # 用户绑定 openid
        try:
            OAuthQQUser.objects.create(openid=openid,
                                       user=user)
        except Exception:
            return JsonResponse({'code': 400,
                                 'errmsg': '往数据库添加数据出错'})

        login(request, user)
        response = JsonResponse({'code': 0,
                                 'errmsg': 'ok'})
        response.set_cookie('username',
                            user.username,
                            max_age=3600 * 24 * 14)
        return response
