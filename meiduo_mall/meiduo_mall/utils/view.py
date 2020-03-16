from django.http import JsonResponse


def my_decorator(view):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        else:
            return JsonResponse({'code': 400,
                                 'errmsg': '请登录后重试'})

    return wrapper


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, *args, **kwargs):
        view = super().as_view(*args, **kwargs)
        return my_decorator(view)
