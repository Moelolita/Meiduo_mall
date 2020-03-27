from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage
from django.views import View
from goods.models import SKU, GoodsCategory
from django.http import JsonResponse
from goods.utils import get_breadcrumb
from haystack.views import SearchView


# Create your views here.


class ListView(View):
    """商品列表页"""

    def get(self, request, category_id):
        """提供商品列表页"""
        page_num = request.GET.get('page')
        page_size = request.GET.get('page_size')
        sort = request.GET.get('ordering')

        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return JsonResponse({'code': 400,
                                 'errmsg': '获取mysql数据出错'})

        breadcrumb = get_breadcrumb(category)
        # 排序方式
        try:
            skus = SKU.objects.filter(category=category,
                                      is_launched=True).order_by(sort)
        except SKU.DoesNotExist:
            return JsonResponse({'code': 400,
                                 'errmsg': '获取mysql数据出错'})

        paginator = Paginator(skus, 5)

        try:
            page_skus = paginator.page(page_num)
        except EmptyPage:
            return JsonResponse({'code': 400,
                                 'errmsg': '获取page数据出错'})
        # 获取总页数
        total_page = paginator.num_pages

        list = []
        for sku in page_skus:
            list.append({
                'id': sku.id,
                'default_image_url': sku.default_image_url,
                'name': sku.name,
                'price': sku.price
            })

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'breadcrumb': breadcrumb,  # 面包屑导航
            'list': list,
            'count': total_page
        })


class HotGoodsView(View):
    """商品热销排行"""

    def get(self, request, category_id):
        try:
            skus = SKU.objects.filter(category_id=category_id,
                                      is_launched=True).order_by('-sales')[:2]
        except Exception as error:
            return JsonResponse({'code': 400,
                                 'errmsg': '获取商品出错'})
        hot_skus = []
        for sku in skus:
            hot_skus.append({
                'id': sku.id,
                'default_image_url': sku.default_image_url,
                'name': sku.name,
                'price': sku.price
            })
        return JsonResponse({'code': 0,
                             'errmsg': 'OK',
                             'hot_skus': hot_skus})


class MySearchView(SearchView):
    """重写Search类"""

    def create_response(self):
        page = self.request.GET.get('page')
        context = self.get_context()
        data_list = []
        for sku in context['page'].object_list:
            data_list.append({
                'id': sku.object.id,
                'name': sku.object.name,
                'price': sku.object.price,
                'default_image_url': sku.object.default_image_url,
                'searchkey': context.get('query'),
                'page_size': context['page'].paginator.num_pages,
                'count': context['page'].paginator.count
            })
        return JsonResponse(data_list, safe=False)
