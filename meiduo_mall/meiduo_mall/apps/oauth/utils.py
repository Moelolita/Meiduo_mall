from itsdangerous import TimedJSONWebSignatureSerializer
from django.conf import settings


def generate_access_token(openid):
    """对传入的 openid 进行加密处理, 返回 token"""

    # QQ 登录保存用户数据的 token 有效期
    # settings.SECRET_KEY: 加密使用的秘钥
    # 过期时间: 600s = 10min
    serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY,
                                                 expires_in=600)
    data = {'openid': openid}

    # 对 dict 进行加密
    token = serializer.dumps(data)

    # 加密完之后, 解码返回.
    return token.decode()


def check_access_token(access_token):
    """把access_token解密为openid"""

    # 用导入的类创建对象
    # obj = TimedJSONWebSignatureSerializer(秘钥, 有效期)
    obj = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, expires_in=3600)

    data = obj.loads(access_token)

    return data.get('openid')
