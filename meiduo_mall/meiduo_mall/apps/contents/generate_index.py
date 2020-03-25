from collections import OrderedDict
from django.conf import settings
from django.template import loader
import os
import time
from goods.models import GoodsChannel, GoodsCategory
from contents.models import ContentCategory, Content


def generate_static_index_html():
    categories = OrderedDict()

    channels = GoodsCategory.objects.order_by('group_id',
                                              'sequence')
    for channel in channels:
        group_id = channels.group_id
        if group_id not in categories:
            categories[group_id] = {
                'channels': [],
                'sub_cats': []
            }
        cat1 = channel.category
        categories[group_id]['channels'].append({
            'id': cat1.id,
            'name': cat1.name,
            'url': channel.url
        })
        cat2s = GoodsCategory.objects.filter(parent=cat1)
        for cat2 in cat2s:
            cat2.sub_cats = []
            cat3s = GoodsCategory.objects.filter(parent=cat2)
            for cat3 in cat3s:
                cat2.sub_cats.append(cat2)

    contents = {}
    content_categories = ContentCategory.objects.all()
    for cat in content_categories:
        contents[cat.key] = Content.objects.filter(category=cat,
                                                   status=True).order_by('sequence')

    context = {
        'categories': categories,
        'contents': contents
    }
    template = loader.get_template('index.html')
    html_text = template.render(context)
    file_path = os.path.join(settings.GENERATED_STATIC_HTML_FILES_DIR, 'index.html')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_text)
