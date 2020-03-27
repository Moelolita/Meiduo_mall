from collections import OrderedDict
from django.conf import settings
from django.template import loader
import os
from goods.models import GoodsChannel, GoodsCategory
from contents.models import ContentCategory, Content


def generate_static_index_html():
    """生成首页静态文件"""
    dict = OrderedDict()
    try:
        channels = GoodsChannel.objects.all().order_by('group_id',
                                                       'sequence')
        for channel in channels:
            group_id = channel.group_id
            if group_id not in dict:
                dict[group_id] = {
                    'channels': [],
                    'sub_cats': []
                }
            cat1 = channel.category
            dict.get(group_id).get('channels').append({
                'id': cat1.id,
                'name': cat1.name,
                'url': channel.url
            })
            cat2s = GoodsCategory.objects.filter(parent=cat1)
            for cat2 in cat2s:
                cat2.sub_cats = []
                cat3s = GoodsCategory.objects.filter(parent=cat2)
                for cat3 in cat3s:
                    cat2.sub_cats.append(cat3)
                dict.get(group_id).get('sub_cats').append(cat2)
    except Exception as error:
        raise Exception('数据库获取失败')
    try:
        cats = ContentCategory.objects.all()
        new_dict = {}
        for cat in cats:
            content = Content.objects.filter(category=cat,
                                             status=True).order_by('sequence')
            new_dict[cat.key] = content
    except Exception as error:
        raise Exception('广告数据获取失败')
    context = {
        'categories': dict,
        'contents': new_dict
    }
    template = loader.get_template('indexes.html')
    html_text = template.render(context)
    file_path = os.path.join(settings.GENERATED_STATIC_HTML_FILES_DIR, 'indexes.html')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_text)
