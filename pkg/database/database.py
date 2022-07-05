import json
import time

import pymysql as pymysql
import requests


def raw_to_escape(raw):
    return raw.replace("\\", "\\\\").replace('\'', '‘')

def get_qq_nickname(uin):
    url = "https://r.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg?g_tk=1518561325&uins={}".format(uin)
    response = requests.get(url)
    text = response.content.decode('gbk', 'ignore')
    json_data = json.loads(text.replace("portraitCallBack(", "")[:-1])
    nickname=json_data[str(uin)][6]
    return nickname

class MySQLConnection:
    connection = None
    cursor = None

    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

        self.connect()

    def connect(self):
        self.connection = pymysql.connect(host=self.host,
                                          port=self.port,
                                          user=self.user,
                                          password=self.password,
                                          db=self.database,
                                          autocommit=True,
                                          charset='utf8mb4', )
        self.cursor = self.connection.cursor()

    def ensure_connection(self, attempts=3):
        for i in range(attempts):
            try:
                self.connection.ping()
                return i
            except:
                self.connect()
                if i == attempts - 1:
                    raise Exception('MySQL连接失败')
            time.sleep(2)

    def register(self, openid: str, uin):

        self.ensure_connection()
        sql = "select * from `accounts` where `qq`='{}'".format(uin)
        self.cursor.execute(sql)
        results = self.cursor.fetchall()
        for _ in results:
            # 只要有
            raise Exception("该QQ号已经绑定了微信号,请先发送 #unbinding 以解绑")

        sql = "insert into `accounts` (`qq`,`openid`,`timestamp`) values ('{}','{}',{})".format(uin, openid,
                                                                                                int(time.time()))
        self.cursor.execute(sql)
        # self.connection.commit()

    def unbinding(self, uin):
        self.ensure_connection()
        sql = "delete from `accounts` where `qq`='{}'".format(uin)
        self.cursor.execute(sql)
        # self.connection.commit()

    def post_new(self, text: str, media: str, anonymous: bool, qq: int, openid: str):
        sql = "insert into `posts` (`openid`,`qq`,`timestamp`,`text`,`media`,`anonymous`) values ('{}','{}',{},'{}'," \
              "'{}',{})".format(openid, qq, int(time.time()), raw_to_escape(text), media, 1 if anonymous else 0)
        self.cursor.execute(sql)
        # self.connection.commit()

        sql = "select `id` from `posts` where `openid`='{}' order by `id` desc limit 1".format(openid)
        self.cursor.execute(sql)
        result = self.cursor.fetchone()
        return result[0]

    def pull_one_post(self, post_id=-1, status='', openid='', order='asc'):
        results = self.pull_posts(post_id, status, openid, order, capacity=1)
        if len(results) > 0:
            return results['posts'][0]
        else:
            return {'result': 'err:no result'}

    def pull_posts(self, post_id=-1, status='', openid='', order='asc', capacity=10, page=1):
        self.ensure_connection()
        where_statement = ''
        if post_id != -1:
            where_statement = "and `id`={}".format(post_id)
        if status != '' and status != '所有':
            where_statement += " and `status`='{}'".format(status)
        if openid != '':
            where_statement += " and `openid`='{}'".format(openid)

        limit_statement = ''
        if capacity != -1:
            limit_statement = "limit {},{}".format((page - 1) * capacity, capacity)

        # 计算总数
        sql = "select count(*) from `posts` where 1=1 {} order by `id` {}".format(where_statement, order)
        self.cursor.execute(sql)
        total = self.cursor.fetchone()[0]

        sql = "select * from `posts` where 1=1 {} order by `id` {} {}".format(where_statement, order, limit_statement)
        self.cursor.execute(sql)
        results = self.cursor.fetchall()

        posts = []
        for res in results:
            posts.append({
                'result': 'success',
                'id': res[0],
                'openid': res[1],
                'qq': res[2],
                'timestamp': res[3],
                'text': res[4],
                'media': res[5],
                'anonymous': res[6],
                'status': res[7],
                'review': res[8]
            })
        result = {
            'result': 'success',
            'page': page,
            'page_list': [i for i in range(1, int(total / capacity) + (2 if total % capacity > 0 else 1))],
            'total_amount': total,
            'status': status,
            'posts': posts
        }

        return result

    def update_post_status(self, post_id, new_status, review='', old_status=''):
        self.ensure_connection()
        sql = "select `status` from `posts` where `id`={}".format(post_id)
        self.cursor.execute(sql)
        result = self.cursor.fetchone()

        if result is None:
            raise Exception("无此稿件:{}".format(post_id))

        if old_status != '':
            if result[0] != old_status:
                raise Exception("此稿件状态不是:{}".format(old_status))
        self.ensure_connection()
        sql = "update `posts` set `status`='{}' where `id`={}".format(new_status, post_id)
        self.cursor.execute(sql)
        if review != '':
            sql = "update `posts` set `review`='{}' where `id`={}".format(review, post_id)
            self.cursor.execute(sql)
        # self.connection.commit()

    def pull_log_list(self, capacity=10, page=1):
        self.ensure_connection()
        limit_statement = "limit {},{}".format((page - 1) * capacity, capacity)

        sql = "select count(*) from `logs` order by `id` desc"
        self.cursor.execute(sql)
        total = self.cursor.fetchone()[0]

        sql = "select * from `logs` order by `id` desc {}".format(limit_statement)
        self.cursor.execute(sql)
        logs = self.cursor.fetchall()

        result = {'result': 'success', 'logs': []}
        for log in logs:
            result['logs'].append({
                'id': log[0],
                'timestamp': log[1],
                'location': log[2],
                'account': log[3],
                'operation': log[4],
                'content': log[5],
                'ip': log[6]
            })

        result['page'] = page
        result['page_list'] = [i for i in range(1, int(total / capacity) + (2 if total % capacity > 0 else 1))]
        return result

    def fetch_qq_accounts(self, openid):
        self.ensure_connection()

        result = {
            'isbanned': False,
        }

        # 检查是否被封禁
        sql = "select * from `banlist` where `openid`='{}' order by id desc".format(openid)
        self.cursor.execute(sql)
        ban = self.cursor.fetchone()
        if ban is not None:
            start_time = ban[2]
            expire_time = ban[3]
            reason = ban[4]
            if time.time() < expire_time:
                result['isbanned'] = True
                result['start'] = start_time
                result['expire'] = expire_time
                result['reason'] = reason
                return result

        sql = "select * from `accounts` where `openid`='{}'".format(openid)
        self.cursor.execute(sql)
        accounts = self.cursor.fetchall()

        result['accounts'] = []
        for account in accounts:
            # 获取nick
            result['accounts'].append({
                'id': account[0],
                'qq': account[2],
                'nick':get_qq_nickname(account[2]),
                'resgister_time': account[3],
                'identity': account[4],
            })

        return result

    def fetch_constant(self, key):
        self.ensure_connection()
        sql = "select * from `constants` where `key`='{}'".format(key)
        self.cursor.execute(sql)
        row = self.cursor.fetchone()

        result = {
            'result': 'success',
            'exist': False,
            'value': ''
        }

        if row is None:
            result['exist'] = False
        else:
            result['exist'] = True
            result['value'] = row[1]

        return result

    def fetch_service_list(self):
        self.ensure_connection()
        sql = "select * from `services`"
        self.cursor.execute(sql)
        services = self.cursor.fetchall()

        result = {
            'result': 'success',
            'services': []
        }

        for service in services:
            if service[6] != 1:
                continue
            result['services'].append({
                'id': service[0],
                'name': service[1],
                'description': service[2],
                'order': service[3],
                'page_url': service[4],
                'color': service[5],
                'enable': service[6],
                'external_url': service[7],
            })

        return result

    def fetch_static_data(self, key):
        self.ensure_connection()
        sql = "select * from `static_data` where `key`='{}'".format(key)
        self.cursor.execute(sql)
        row = self.cursor.fetchone()

        result = {
            'result': 'success',
            'timestamp': 0,
            'content': ''
        }

        if row is not None:
            result['timestamp'] = row[1]
            result['content'] = row[2]

        return result

    def fetch_content_list(self, capacity, page):
        self.ensure_connection()
        limit_statement = "limit {},{}".format((page - 1) * capacity, capacity)
        sql = "select count(*) \nfrom (\n\tselect p.id pid,p.openid,e.id eid,p.`status` `status`,(\n\t\tcase \n\t\twhen p.`timestamp`is null\n\t\tthen e.`timestamp`\n\t\twhen e.`timestamp`is null\n\t\tthen p.`timestamp`\n\t\twhen (e.`timestamp` is not null) and (p.`timestamp`is not null)\n\t\tthen greatest(p.`timestamp`,e.`timestamp`)\n\t\tend\n\t) gr_time from posts p\n\tleft outer join emotions e\n\ton p.id=e.pid\n    \n\tunion\n    \n\tselect p.id pid,p.openid,e.id eid,p.`status` `status`,(\n\t\tcase \n\t\twhen p.`timestamp`is null\n\t\tthen e.`timestamp`\n\t\twhen e.`timestamp`is null\n\t\tthen p.`timestamp`\n\t\twhen (e.`timestamp` is not null) and (p.`timestamp`is not null)\n\t\tthen greatest(p.`timestamp`,e.`timestamp`)\n\t\tend\n\t) gr_time from posts p\n\tright outer join emotions e\n\ton p.id=e.pid\n) t\norder by gr_time desc"
        self.cursor.execute(sql)
        total = self.cursor.fetchone()[0]

        sql = "select * \nfrom (\n\tselect coalesce(p.id,-1) pid,coalesce(p.openid,''),coalesce(-1,e.id) eid,coalesce(e.eid,'') euid,coalesce( p.`status`,'已发表') `status`,(\n\t\tcase \n\t\twhen p.`timestamp`is null\n\t\tthen e.`timestamp`\n\t\twhen e.`timestamp`is null\n\t\tthen p.`timestamp`\n\t\twhen (e.`timestamp` is not null) and (p.`timestamp`is not null)\n\t\tthen greatest(p.`timestamp`,e.`timestamp`)\n\t\tend\n\t) gr_time from posts p\n\tleft outer join emotions e\n\ton p.id=e.pid\n    \n\tunion\n    \n\tselect coalesce(p.id,-1) pid,coalesce(p.openid,''),coalesce(-1,e.id) eid,coalesce(e.eid,'') euid,coalesce( p.`status`,'已发表') `status`,(\n\t\tcase \n\t\twhen p.`timestamp`is null\n\t\tthen e.`timestamp`\n\t\twhen e.`timestamp`is null\n\t\tthen p.`timestamp`\n\t\twhen (e.`timestamp` is not null) and (p.`timestamp`is not null)\n\t\tthen greatest(p.`timestamp`,e.`timestamp`)\n\t\tend\n\t) gr_time from posts p\n\tright outer join emotions e\n\ton p.id=e.pid\n) t\norder by gr_time desc " + limit_statement
        self.cursor.execute(sql)
        contents = self.cursor.fetchall()

        result = {
            'result': 'success',
            'amt': total,
            'page': page,
            'capacity': capacity,
            'contents': []
        }

        for content in contents:
            content_result = {
                'pid': content[0],
                'openid': content[1],
                'eid': content[2],
                'euid': content[3],
                'status': content[4],
                'timestamp': content[5],
            }

            if content[3] != '':
                # 检出所有点赞记录
                sql = "select `timestamp`,json from `events` where `type`='liker_record' and `json` like '%{}%' order by `timestamp`;".format(
                    content[3])
                self.cursor.execute(sql)
                liker_record_rows = self.cursor.fetchall()

                # 结果
                like_records = []
                for liker_record in liker_record_rows:
                    # 加载liker_record的json
                    json_obj = json.loads(liker_record[1])

                    like_records.append([liker_record[0], json_obj['interval'], json_obj['like']])
                content_result['like_records'] = like_records

            result['contents'].append(content_result)
        return result

    def user_feedback(self, openid, content, media):
        self.ensure_connection()
        sql = "insert into `feedback`(`openid`,`content`,`timestamp`,`media`) values('{}','{}',{},'{}')".format(openid, content,int(time.time()), media)
        self.cursor.execute(sql)
        return 'success'