# 配置文件
import logging

# QQ机器人账号
qq_bot_uin = 0

# mirai-http的verifykey
mirai_http_verify_key = 'yirimirai'

# QQ空间账号
qzone_uin = 0

# 预置Qzone cookie,若没有,将会在启动时请求管理员扫码
qzone_cookie = ''

# 自动回复消息
auto_reply_message = '[bot]bot收到私发QQ消息时回复的文字\n\n'

# 小程序码路径
qrcode_path = './qrcode.jpg'

# 管理员QQ，用于接收系统内部通知
admin_uins = [1111111111]

# 管理群，用于审核说说
admin_groups = [1234567890]

# MySQL数据库
database_context = {
    'host': 'localhost',
    'port': 3306,
    'user': 'camwall',
    'password': '123456',
    'db': 'camwall'
}

# RESTful API 监听端口
api_port = 8989

# RESTful API 域名
api_domain = 'localhost'

# RESTful API SSL 证书路径
api_ssl_context = (
    './cert/cert.pem',
    './cert/key.pem'
)

# 小程序云开发的环境id
cloud_env_id = 'dev-0'

# 小程序的appid
mini_program_appid = 'wx8f8f8f8f8f8f8f8f'

# 小程序的secret
mini_program_secret = '1234567890'

# logging的日志级别
logging_level = logging.INFO
