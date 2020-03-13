from users.models import User
from django.views import View
from django.http import JsonResponse


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
