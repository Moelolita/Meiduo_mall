import json
import re
from django.views import View
from django.http import JsonResponse
from django.contrib.auth import login, authenticate, logout
from django_redis import get_redis_connection
from meiduo_mall.utils.view import LoginRequiredMixin
from users.models import User, Address
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
        sms_code_client = sms_code_server
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

        response = JsonResponse({'code': 0,
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


class CreateAddressView(View):
    """新增地址"""

    def post(self, request):
        try:
            count = Address.objects.filter(user=request.user,
                                           is_deleted=False).count()
        except Exception as error:
            return JsonResponse({'code': 400,
                                 'errmsg': '获取地址数据出错'})
        # 判断地址上限
        if count >= 20:
            return JsonResponse({'code': 400,
                                 'errmsg': '超过地址数量上限'})

        # 接收参数
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 整体检验
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return JsonResponse({'code': 400,
                                 'errmsg': '缺少必传参数'})
        # 手机号检验
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({'code': 400,
                                 'errmsg': '参数mobile有误'})
        # 固定电话检验
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return JsonResponse({'code': 400,
                                     'errmsg': '参数tel有误'})
        # 邮箱检验
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return JsonResponse({'code': 400,
                                     'errmsg': '参数email有误'})

        # 保存地址信息
        try:
            address = Address.objects.create(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )

            # 设置默认地址
            if not request.user.default_address:
                request.user.default_address = address
                request.user.save()
        except Exception as error:
            logger.error(error)
            return JsonResponse({'code': 400,
                                 'errmsg': '新增地址失败'})
        # 成功后返回前端实现局部刷新
        address_dict = {
            'id': address.id,
            'title': address.title,
            'receiver': address.receiver,
            'province': address.province.name,
            'city': address.city.name,
            'district': address.district.name,
            'place': address.place,
            'mobile': address.mobile,
            'tel': address.tel,
            'email': address.email
        }

        return JsonResponse({'code': 0,
                             'errmsg': '新增地址成功',
                             'address': address_dict})


class AddressView(View):
    """用户收货地址"""

    def get(self, request):
        """提供地址管理界面"""
        # 获取所有地址
        addresses = Address.objects.filter(user=request.user,
                                           is_deleted=False)
        address_dict_list = []
        for address in addresses:
            address_dict = {
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "city": address.city.name,
                "district": address.district.name,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }
            default_address = request.user.default_address
            if default_address.id == address.id:
                address_dict_list.insert(0, address_dict)
            else:
                address_dict_list.append(address_dict)

        default_id = request.user.default_address_id
        return JsonResponse({'code': 0,
                             'errmsg': 'ok',
                             'addresses': address_dict_list,
                             'default_address_id': default_id})


class UpdateDestroyAddressView(View):
    """修改与删除地址"""

    def put(self, request, address_id):
        """修改地址"""
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 整体检验
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return JsonResponse({'code': 400,
                                 'errmsg': '缺少必传参数'})
        # 邮箱检验
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({'code': 400,
                                 'errmsg': '参数mobile有误'})
        # 固定电话检验
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return JsonResponse({'code': 400,
                                     'errmsg': '参数tel有误'})
        # 邮箱检验
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return JsonResponse({'code': 400,
                                     'errmsg': '参数email有误'})
        # 判断地址是否存在,并更新地址信息
        try:
            Address.objects.filter(id=address_id).update(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
        except Exception as error:
            logger.error(error)
            return JsonResponse({'code': 400,
                                 'errmsg': '更新地址失败'})
        # 构造返回数据
        address = Address.objects.get(id=address_id)
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }
        return JsonResponse({'code': 0,
                             'errmsg': '更新地址成功',
                             'address': address_dict})

    def delete(self, request, address_id):
        """删除地址"""
        try:
            # 查询要删除的地址
            address = Address.objects.get(id=address_id)
            # 逻辑删除
            address.is_deleted = True
            address.save()
        except Exception as error:
            logger.error(error)
            return JsonResponse({'code': 400,
                                 'errmsg': '删除地址失败'})
        return JsonResponse({'code': 0,
                             'errmsg': '删除地址成功'})
