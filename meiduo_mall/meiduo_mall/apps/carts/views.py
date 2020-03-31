import base64
import json
import pickle

from django import http
from django.views import View
from django_redis import get_redis_connection
from goods.models import SKU
from django.shortcuts import render


# Create your views here.


class CartsView(View):
    """购物车管理"""

    def post(self, request):
        """添加购物车"""
        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)

        # 判断参数是否齐全
        if not all([sku_id, count]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断sku_id是否存在
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品不存在')
        # 判断count是否为数字
        try:
            count = int(count)
        except Exception:
            return http.HttpResponseForbidden('参数count有误')
        # 判断selected是否为bool值
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        # 判断用户是否登录
        if request.user.is_authenticated:
            # 用户已登录，操作redis购物车
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            # 新增购物车数据
            pl.hincrby('carts_%s' % request.user.id,
                       sku_id,
                       count)
            # 新增选中的状态
            if selected:
                pl.sadd('selected_%s' % request.user.id,
                        sku_id)
            # 执行管道
            pl.execute()

            # 响应结果
            return http.JsonResponse({'code': 0,
                                      'errmsg': '添加购物车成功'})
        else:
            # 用户未登录，操作cookie购物车
            cookie_cart = request.COOKIES.get('carts')
            # 如果用户操作过 cookie 购物车
            if cookie_cart:
                # 将 cookie_cart 转成 base64 的 bytes,最后将 bytes 转字典
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            else:
                # 用户从没有操作过 cookie 购物车
                cart_dict = {}

            # 判断要加入购物车的商品是否已经在购物车中
            # 如有相同商品，累加求和，反之，直接赋值
            # 我们判断用户之前是否将该商品加入过购物车, 如果加入过
            # 则只需要让数量增加即可.
            # 如果没有存在过, 则需要创建, 然后增加:
            # 形式如下所示:
            # {
            #     '<sku_id>': {
            #         'count': '<count>',
            #         'selected': '<selected>',
            #     },
            #     ...
            # }
            if sku_id in cart_dict:
                # 累加求和
                count += cart_dict[sku_id]['count']

            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }
            # 将字典转成 bytes,再将 bytes 转成 base64 的 bytes
            # 最后将bytes转字符串
            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()

            # 创建响应对象
            response = http.JsonResponse({'code': 0,
                                          'errmsg': '添加购物车成功'})
            # 响应结果并将购物车数据写入到 cookie
            response.set_cookie('carts', cart_data)

            return response

    def get(self, request):
        """展示购物车"""
        user = request.user
        if user.is_authenticated:
            # 用户已登录，查询redis购物车
            # 用户已登录，查询 redis 购物车
            redis_conn = get_redis_connection('carts')
            # 获取 redis 中的购物车数据
            item_dict = redis_conn.hgetall('carts_%s' % user.id)
            # 获取 redis 中的选中状态
            cart_selected = redis_conn.smembers('selected_%s' % user.id)

            # 将 redis 中的数据构造成跟 cookie 中的格式一致
            # 方便统一查询
            cart_dict = {}
            for sku_id, count in item_dict.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in cart_selected
                }
        else:
            # 用户未登录，查询cookies购物车
            cookie_cart = request.COOKIES.get('carts')
            if cookie_cart:
                # 将cart_str转成bytes,再将bytes转成base64的bytes,
                # 最后将bytes转字典
                cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
            else:
                cart_dict = {}

            # 构造购物车渲染数据
            sku_ids = cart_dict.keys()
            skus = SKU.objects.filter(id__in=sku_ids)
            cart_skus = []
            for sku in skus:
                cart_skus.append({
                    'id': sku.id,
                    'name': sku.name,
                    'count': cart_dict.get(sku.id).get('count'),
                    'selected': cart_dict.get(sku.id).get('selected'),
                    'default_image_url': sku.default_image_url,
                    'price': sku.price,
                    'amount': sku.price * cart_dict.get(sku.id).get('count'),
                })

            # 渲染购物车页面
            return http.JsonResponse({'code': 0,
                                      'errmsg': 'ok',
                                      'cart_skus': cart_skus})

    def put(self, request):
        """修改购物车"""
        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)

        # 判断参数是否齐全
        if not all([sku_id, count]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断sku_id是否存在
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品sku_id不存在')
        # 判断count是否为数字
        try:
            count = int(count)
        except Exception:
            return http.HttpResponseForbidden('参数count有误')
        # 判断selected是否为bool值
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 用户已登录，修改redis购物车
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            # 因为接口设计为幂等的，直接覆盖
            pl.hset('carts_%s' % user.id, sku_id, count)
            # 是否选中
            if selected:
                pl.sadd('selected_%s' % user.id, sku_id)
            else:
                pl.srem('selected_%s' % user.id, sku_id)
            pl.execute()

            # 创建响应对象
            cart_sku = {
                'id': sku_id,
                'count': count,
                'selected': selected,
                'name': sku.name,
                'default_image_url': sku.default_image_url,
                'price': sku.price,
                'amount': sku.price * count,
            }
            return http.JsonResponse({'code': 0,
                                      'errmsg': '修改购物车成功',
                                      'cart_sku': cart_sku})
        else:
            # 用户未登录，修改cookie购物车
            cookie_cart = request.COOKIES.get('carts')
            if cookie_cart:
                # 将cookie_cart转成bytes,再将bytes转成base64的bytes,最后将bytes转字典
                cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
            else:
                cart_dict = {}
            # 因为接口设计为幂等的，直接覆盖
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }
            # 将字典转成bytes,再将bytes转成base64的bytes,最后将bytes转字符串
            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()

            # 创建响应对象
            cart_sku = {
                'id': sku_id,
                'count': count,
                'selected': selected
            }
            response = http.JsonResponse({'code': 0,
                                          'errmsg': '修改购物车成功',
                                          'cart_sku': cart_sku})
            # 响应结果并将购物车数据写入到cookie
            response.set_cookie('carts', cart_data)

            return response

    def delete(self, request):
        """删除购物车"""
        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')

        # 判断sku_id是否存在
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品不存在')

        # 判断用户是否登录
        user = request.user
        if user is not None and user.is_authenticated:
            # 用户未登录，删除redis购物车
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            # 删除键，就等价于删除了整条记录
            pl.hdel('carts_%s' % user.id, sku_id)
            pl.srem('selected_%s' % user.id, sku_id)
            pl.execute()

            # 删除结束后，没有响应的数据，只需要响应状态码即可
            return http.JsonResponse({'code': 0,
                                      'errmsg': '删除购物车成功'})
        else:
            # 用户未登录，删除cookie购物车
            cookie_cart = request.COOKIES.get('carts')
            if cookie_cart:
                # 将cookie_cart转成bytes,再将bytes转成base64的bytes,最后将bytes转字典
                cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
            else:
                cart_dict = {}

            # 创建响应对象
            response = http.JsonResponse({'code': 0,
                                          'errmsg': '删除购物车成功'})
            if sku_id in cart_dict:
                del cart_dict[sku_id]
                # 将字典转成bytes,再将bytes转成base64的bytes,最后将bytes转字符串
                cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
                # 响应结果并将购物车数据写入到cookie
                response.set_cookie('carts', cart_data)

            return response


class CartSelectAllView(View):
    """全选购物车"""

    def put(self, request):
        # 接收参数
        json_dict = json.loads(request.body.decode())
        selected = json_dict.get('selected', True)

        # 校验参数
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 用户已登录，操作redis购物车
            redis_conn = get_redis_connection('carts')
            item_dict = redis_conn.hgetall('carts_%s' % user.id)
            sku_ids = item_dict.keys()

            if selected:
                # 全选
                redis_conn.sadd('selected_%s' % user.id, *sku_ids)
            else:
                # 取消全选
                redis_conn.srem('selected_%s' % user.id, *sku_ids)

            return http.JsonResponse({'code': 0,
                                      'errmsg': '全选购物车成功'})
        else:
            # 用户已登录，操作cookie购物车
            cookie_cart = request.COOKIES.get('carts')
            response = http.JsonResponse({'code': 0,
                                          'errmsg': '全选购物车成功'})
            if cookie_cart:
                cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))

                for sku_id in cart_dict.keys():
                    cart_dict[sku_id]['selected'] = selected

                cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()

                response.set_cookie('carts', cart_data)

            return response


class CartsSimpleView(View):
    """商品页面右上角购物车"""

    def get(self, request):
        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 用户已登录，查询 Redis 购物车
            redis_conn = get_redis_connection('carts')
            item_dict = redis_conn.hgetall('carts_%s' % user.id)
            cart_selected = redis_conn.smembers('selected_%s' % user.id)

            # 将 redis 中的两个数据统一格式，跟 cookie 中的格式一致，方便统一查询
            cart_dict = {}
            for sku_id, count in item_dict.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in cart_selected
                }
        else:
            # 用户未登录，查询 cookie 购物车
            cookie_cart = request.COOKIES.get('carts')
            if cookie_cart:
                cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
            else:
                cart_dict = {}

        # 构造简单购物车 JSON 数据
        cart_skus = []
        sku_ids = cart_dict.keys()
        skus = SKU.objects.filter(id__in=sku_ids)
        for sku in skus:
            cart_skus.append({
                'id': sku.id,
                'name': sku.name,
                'count': cart_dict.get(sku.id).get('count'),
                'default_image_url': sku.default_image_url
            })

        # 响应 json 列表数据
        return http.JsonResponse({'code': 0,
                                  'errmsg': 'OK',
                                  'cart_skus': cart_skus})
