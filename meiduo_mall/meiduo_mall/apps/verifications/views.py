from django.shortcuts import render
import random
from django import http
from django.views import View
from django_redis import get_redis_connection
from meiduo_mall.libs.captcha.captcha import captcha
from meiduo_mall.libs.yuntongxun.ccp_sms import CCP
from celery_tasks.sms.tasks import ccp_send_sms_code
import logging

logger = logging.getLogger('django')


# Create your views here.
class ImageCodeView(View):
    """图形验证码"""

    def get(self, request, uuid):
        # 得到图形验证码
        text, image = captcha.generate_captcha()
        # 链接redis数据库
        redis_conn = get_redis_connection('verify_code')
        # 设置图形验证码
        try:
            redis_conn.setex('img_%s' % uuid, 300, text)
        except Exception as error:
            logger.error(error)
        return http.HttpResponse(image, content_type='image/jpg')


class SMSCodeView(View):
    """短信验证码"""
    def get(self, request, mobile):
        # 链接到redis数据库,获取手机号
        redis_conn = get_redis_connection('verify_code')
        send_flag = redis_conn.get('send_flag_%s' % mobile)
        if send_flag:
            return http.JsonResponse({'code': 400,
                                      'errmsg': '发送过于频繁'})
        # 接受前端参数
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')
        # 整体校验
        if not all([image_code_client, uuid]):
            return http.JsonResponse({'code': 400,
                                      'errmsg': '缺少必要参数'})
        # 获取图形验证码
        image_code_server = redis_conn.get('img_%s' % uuid)
        # 图形验证码校验
        if image_code_server is None:
            return http.JsonResponse({'code': 400,
                                      'errmsg': '图形验证码失效'})
        # 删除redis中图形验证码
        try:
            redis_conn.delete('img_%s' % uuid)
        except Exception as error:
            logger.error(error)
        # 服务端图形验证码转换
        image_code_server = image_code_server.decode()
        # 图形验证码对比
        if image_code_client.lower() != image_code_server.lower():
            return http.JsonResponse({'code': 400,
                                      'errmsg': '输入有误'})
        # 生成6位短信验证码
        # sms_code = '%06d' % random.randint(0, 999999)
        sms_code = 123456
        logger.info(sms_code)
        # 创建管道并执行
        pl = redis_conn.pipeline()
        pl.setex('sms_%s' % mobile, 300, sms_code)
        pl.setex('send_flag_%s' % mobile, 60, 1)
        pl.execute()
        # 发送短信
        # CCP().send_template_sms(mobile, [sms_code, 5], 1)
        ccp_send_sms_code.delay(mobile, sms_code)
        return http.JsonResponse({'code': 0,
                                  'errmsg': '发送成功'})
