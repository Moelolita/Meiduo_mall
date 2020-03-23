from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.core.cache import cache
from areas.models import Area


# Create your views here.
class ProvinceAreasView(View):
    """省级"""

    def get(self, request):
        province_list = cache.get('province_list')
        if not province_list:
            try:
                province_model_list = Area.objects.filter(parent__isnull=True)
                province_list = []
                for province_model in province_model_list:
                    province_list.append({'id': province_model.id,
                                          'name': province_model.name})

                cache.set('province_list', province_list, 3600)

            except Exception as error:
                return JsonResponse({'code': 400,
                                     'errmsg': '省份数据错误'})

        return JsonResponse({'code': 0,
                             'errmsg': 'OK',
                             'province_list': province_list})


class SubAreasView(View):
    """子级地区"""

    def get(self, request, pk):
        sub_data = cache.get('sub_area' + pk)
        if not sub_data:
            try:
                sub_model_list = Area.objects.filter(parent=pk)

                parent_model = Area.objects.get(id=pk)

                sub_list = []

                for sub_model in sub_model_list:
                    sub_list.append({'id': sub_model.id,
                                     'name': sub_model.name})

                sub_data = {'id': parent_model.id,  # pk
                            'name': parent_model.name,
                            'subs': sub_list}

                cache.set('sub_area_' + pk, sub_data, 3600)

            except Exception as error:
                return JsonResponse({'code': 400,
                                     'errmsg': '城市或区县数据错误'})

        return JsonResponse({'code': 0,
                             'errmsg': 'OK',
                             'sub_data': sub_data})
