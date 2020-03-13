from django.shortcuts import render
from django.views import View
from django_redis import get_redis_connection
from meiduo_mall.libs.captcha.captcha import captcha

from django import http


# Create your views here.
class ImageCodeView(View):
    def get(self, request, uuid):
        text, image = captcha.generate_captcha()
        redis_conn = get_redis_connection('verify_code')
        redis_conn.setex('img_%s' % uuid, 300, text)
        return http.HttpResponse(image, content_type='image/jpg')
