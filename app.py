import datetime
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

import gunicorn
from exceptiongroup import catch
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import random
import matplotlib.pyplot as plt
from sqlalchemy import text
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import relationship

# 创建线程池
executor = ThreadPoolExecutor(max_workers=10)

def create_app():
    app = Flask(__name__)
    CORS(app)
    return app

app = create_app()
app.debug = True
app.threaded = True

if __name__ == "__main__":
    app.run(threaded=True,debug=True)

host = '127.0.0.1'
port = "3306"
username = 'root'
password = 'ydx56HW2004'
database = 'redpack'

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql://{username}:{password}@{host}:{port}/{database}?charset=utf8"
print(app.config['SQLALCHEMY_DATABASE_URI'])



# app config(连接数据库)
db = SQLAlchemy(app)

class User_db(db.Model):
    __tablename__ = 'user'
    ID = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Numeric(12,2), nullable=False)

    def __init__(self, ID, name, balance):
        self.ID = ID
        self.name = name
        self.balance = balance

    def to_dict(self):
        return {
            "ID": self.ID,
            "name": self.name,
            "balance": self.balance,
        }

class Record_db(db.Model):
    __tablename__ = 'record'
    userid = db.Column(db.Integer, db.ForeignKey('user.ID'), nullable=False)
    redid = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(12,2), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    def __init__(self, userid, redid, amount, time):
        self.userid = userid
        self.redid = redid
        self.amount = amount
        self.time = time

class RedEnvelop_db(db.Model):
    __tablename__ = 'redenvelope'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    totalAmount = db.Column(db.Numeric(12,2), nullable=False)
    describe = db.Column(db.String(100), nullable=False)
    def __init__(self, id, number, totalAmount,describe):
        self.id = id
        self.number = number
        self.totalAmount = totalAmount
        self.describe = describe

class user_red_db(db.Model):
    __tablename__ = 'user_red'
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('user.ID'), nullable=False)
    redid = db.Column(db.Integer, db.ForeignKey('redenvelope.id'), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    def __init__(self, userid, redid, time):
        self.userid = userid
        self.redid = redid
        self.time = time

class redenvelope_split_db(db.Model):
    __tablename__ = 'redenvelope_split'
    id = db.Column(db.Integer, primary_key=True)
    redId = db.Column(db.Integer)
    split_money = db.Column(db.Numeric(12,2), nullable=False)
    def __init__(self, redId, split_money,id):
        self.redId = redId
        self.split_money = split_money
        self.id = id
# 多线程锁
lock = threading.Lock()

class RedPacket:
    def __init__(self, owner,total_money,total_persons,id):
        self.id = id
        self.owner = owner
        self.total_money = total_money
        self.total_persons = total_persons
        self.assignedRed_packets = []
        self.record = []

    def distribute(self):
        remaining_money = self.total_money
        remaining_persons = self.total_persons
        red_packet_amounts = []

        if  self.total_persons*0.01>= self.total_money:
            print("红包分配失败，每个红包至少要0.01")
            return

        for i in range(self.total_persons - 1):
            avg_amount = (remaining_money / remaining_persons) * 2
            if avg_amount < 0.01:
                avg_amount = 0.01
            current_amount = random.uniform(0.01, avg_amount)
            current_amount = round(current_amount, 2)
            red_packet_amounts.append(current_amount)
            remaining_money -= current_amount
            remaining_persons -= 1

        last_amount = round(remaining_money, 2)
        red_packet_amounts.append(last_amount)
        self.assignedRed_packets = red_packet_amounts
        return red_packet_amounts

class Record:
    def __init__(self, userId, packId, money, time):
        self.money = money
        self.userId = userId
        self.packId = packId
        self.time = time

class User:
    def __init__(self, money, name, id):
        self.id = id
        self.name = name
        self.money = money
        self.Red_packets = []
        self.record = []

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.money,
            "age": self.Red_packets,
            "record":self.record
        }

    # 发红包
    def sendPack(self, money, num):
        with lock:
            if self.money - money < 0:
                print("{}余额不足".format(self.name))
                return None

            newred = RedPacket(self,money,num, "{}{}".format(self.name, len(self.record)+1))
            Record(self.id,newred.id,money,datetime.datetime.now())
            self.money -= money
            self.Red_packets.append(newred)

            newred.distribute()
            print("\n{}发了一个红包，总金额为{},个数为{}".format(self.name, money, num))
            print("该红包金额分为：")
            print(newred.assignedRed_packets)
            return newred

    # 抢红包
    def grabPack(self, redpacket):
        with lock:
            if len(redpacket.assignedRed_packets) <= 0:
                print(redpacket.owner.name + "的红包已经抢完了!,{}未抢到红包".format(self.name))
                return 0
            random.shuffle(redpacket.assignedRed_packets)
            value = redpacket.assignedRed_packets.pop(0)
            self.money += value

            # 生成记录
            record = Record(self.id, redpacket.id, value, datetime.datetime.now())

            # 加记录
            self.record.append(record)
            redpacket.record.append(record)

            print("{}抢了{}的红包，金额为{}".format(self.name, redpacket.owner.name, value))
            print("红包列表现在为:{}".format(redpacket.assignedRed_packets))
            return value


# 抢红包线程类
class MyThreadGrap(Thread):
    def __init__(self, user, user2):
        super().__init__()

        self.user2 = user2
        self.user = user
        self.sum = 0
        self.name = user.name

    def run(self):
        self.sum += self.user.grabPack(self.user2.Red_packets[0])


# 发红包线程类
class MyThreadSend(Thread):
    def __init__(self, user, money, pep):
        super().__init__()
        self.user = user
        self.name = user.name
        self.money = money
        self.pep = pep

    def run(self):
        self.user.sendPack(self.money, self.pep)
        print("{}发了{}元红包，还剩{}元".format(self.name, self.money, self.user.money))


# 测试随机算法
def test():
    # 随机算法实现
    def distributeShow(total_money, total_persons):
        remaining_money = total_money
        remaining_persons = total_persons
        red_packet_amounts = []

        for i in range(total_persons - 1):
            avg_amount = (remaining_money / remaining_persons) * 2
            if avg_amount < 0.01:
                avg_amount = 0.01
            current_amount = random.uniform(0.01, avg_amount)
            current_amount = round(current_amount, 2)
            red_packet_amounts.append(current_amount)
            remaining_money -= current_amount
            remaining_persons -= 1

        last_amount = round(remaining_money, 2)
        red_packet_amounts.append(last_amount)
        return red_packet_amounts

    # 设置matplotlib支持中文的字体
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False

    # 测试红包类并绘制100次分配结果的直方图
    total_money = 1000.22  # 总金额
    total_persons = 10  # 总人数
    distribution_results = []
    time = 100000  # 模拟次数

    for i in range(time):
        distribution = distributeShow(total_money, total_persons)
        distribution_results.extend(distribution)
        print("\n第{}轮分配金额".format(i + 1))
        print(distribution)
        print("总金额：")
        print(round(sum(distribution), 2))

    # 绘制直方图
    plt.hist(distribution_results, bins=100, alpha=0.9)
    plt.title('抢红包概率统计({}次模拟)'.format(time))
    plt.xlabel('金额')
    plt.ylabel('次数')
    plt.grid(True)
    plt.show()


# 测试抢红包
def testUserGrap():
    user2 = User(200, "张富钧",1)
    user2.sendPack(100, 10)

    user = User(100, "杨定鑫",2)
    user3 = User(100, "陈俊毅",3)
    user.grabPack(user2.Red_packets[0])
    user3.grabPack(user2.Red_packets[0])


# 测试多线程抢红包
def testMultipleThreadGrab():
    user2 = User(200, "张富钧",0)
    # 发红包
    user2.sendPack(100.22, 10)
    threads = []

    # 抢的总金额
    sum = 0
    # 抢红包线程数
    t = 11
    for i in range(t):
        user = User(100, "杨定鑫{}号：".format(i + 1),i+1)
        threads.append(MyThreadGrap(user, user2))

    for t in threads:
        t.start()

    for t in threads:
        t.join()
        sum += t.sum
    print("抢的总金额为{}".format(round(sum, 2)))


# 测试多线程发红包
def testMultipleThreadSend():
    user2 = User(200000.22, "张富钧",2)

    threads = []

    # 发红包线程数
    t = 11
    for i in range(t):
        # 发红包
        threads.append(MyThreadSend(user2, 1000, 10))

    for t in threads:
        t.start()

    for t in threads:
        t.join()


def main():
    print("**********测试随机算法**********")
    test()
    print("**********测试随机算法**********\n")

    print("**********测试串行抢红包**********")
    testUserGrap()
    print("**********测试串行抢红包**********\n")

    print("**********测试多线程抢红包**********")
    testMultipleThreadGrab()
    print("**********测试多线程抢红包**********")

    print("**********测试多线程发红包**********")
    testMultipleThreadSend()
    print("**********测试多线程发红包**********")


if __name__ == '__main__':
    main()


@app.route('/')
def index():
    # user = User(100000,"ydx",1)
    # future = executor.submit(user.sendPack,100,10)
    # print(future.result().assignedRed_packets)
    # user = User(100000, "ydx", 1)
    # red = user.sendPack(100,10)
    # return "hello"
    user = User_db.query.all()
    # for i in user:
    #     print(i.name)
    # userjson = json.dumps([{"name":i.name,"ID":i.ID,"balance":str(i.balance)} for i in user])
    # print(userjson)

    return json.dumps([{"name":i.name,"ID":i.ID,"balance":str(i.balance)} for i in user])

@app.route('/SendRedpack', methods=['POST'])
def SendRedpack():
    request_data = request.get_json()
    print(request_data)
    describe = request_data['describe']
    totalAmount = float(request_data['totalAmount'])
    number = int(request_data['number'])
    owner = request_data['owner']
    user = User(float(owner['balance']), owner['name'], owner['ID'])
    addredpack = user.sendPack(totalAmount, number)
    print(addredpack.assignedRed_packets)
    try:
        if addredpack == None:
            return dict({"status":"余额不足"})
        new_red_envelop = RedEnvelop_db(
            number=number,
            totalAmount=totalAmount,
            describe=describe,
            id=None
        )
        db.session.add(new_red_envelop)
        db.session.commit()
        redenvId = new_red_envelop.id
        for i in addredpack.assignedRed_packets:
            split = redenvelope_split_db(redId=redenvId, split_money=i,id=None)
            db.session.add(split)
        db.session.commit()
        # 创建发送记录
        user_red_record = user_red_db(userid=owner['ID'], redid=redenvId, time=datetime.datetime.now())
        db.session.add(user_red_record)
        db.session.commit()
        # 用户账户金额减少
        new_user = User_db.query.get(owner['ID'])
        new_user.balance = float(owner['balance'])-totalAmount
        db.session.commit()
    except SQLAlchemyError as e:
        # 如果发生错误，回滚事务
        db.session.rollback()
    return dict({'status': "success"})


@app.route('/GrabRedpack', methods=['POST'])
def GrabRedpack():
    request_data = request.get_json()
    print(request_data)
    envelopToGrab = request_data['envelopToGrab']
    GrabUser = request_data['GrabUser']

    # 是否抢过
    isGrab = request_data['isGrab']

    #抢红包者信息
    name = GrabUser['name']
    Id = GrabUser['ID']
    balance = GrabUser['balance']

    #红包信息
    totalAmount = float(envelopToGrab['totalAmount'])
    envid = envelopToGrab['id']
    number = envelopToGrab['number']
    describe = envelopToGrab['describe']
    time = envelopToGrab['time']
    ownerID = envelopToGrab['ownerID']
    ownerName = envelopToGrab['ownerName']
    ownerBalance = float(envelopToGrab['ownerBalance'])

    if isGrab != 'success':
        # 获取红包分割的第一个
        grabMoney = db.session.execute(text(
            "select split_money from redenvelope_split where redenvelope_split.redId={};".format(envid))).fetchone()

        if grabMoney is None:
            # 删除该红包
            print(envid)
            db.session.execute(text("delete from redenvelope where redenvelope.id={};".format(envid)))
            db.session.commit()
            return dict({'status': "failure", "msg": "红包抢完了"})

        print(grabMoney)
        grabMoney = grabMoney[0]

        # 删除抢到的红包分割
        db.session.execute(text(
            "delete from redenvelope_split where redenvelope_split.redId={} AND redenvelope_split.split_money={};".format(
                envid, grabMoney)))
        db.session.commit()

        # 在抢红包记录中添加记录
        addRecord = Record_db(Id, envid, grabMoney, datetime.datetime.now())
        db.session.add(addRecord)
        db.session.commit()

    # 获取该红包被抢的所有信息
    envGrabData = db.session.execute(text("select userid,redid,amount,time,`user`.`name`,`redenvelope`.`describe` from record INNER JOIN `user` ON `user`.ID=record.userid INNER JOIN redenvelope ON `redenvelope`.id=record.redid where redid={};".format(envid)))
    allEnvGrabData = envGrabData.fetchall()

    # 转换为json,返回
    data = [{"userid":item.userid,"redid":item.redid,"amount":str(item.amount),"time":item.time,"username":item.name,"describe":item.describe} for item in allEnvGrabData]
    print(data)

    # 查询红包名
    red = db.session.execute(text("select * from redenvelope where id = {};".format(envid))).first()

    if isGrab == 'success':
        return dict({
            "grabMoney": 0,
            "totalAmount": totalAmount,
            "envNum": number,
            "grabId": envid,
            "records": data,
            "restNum": number,
            "describe": red.describe
        })

    return dict({
        "grabMoney":grabMoney,
        "totalAmount":totalAmount,
        "envNum":number,
        "grabId":envid,
        "records":data,
        "restNum":number-len(data),
        "describe":red.describe
    })


@app.route('/GetAllUser', methods=['Get'])
def GetAllUser():
    return "hello"

@app.route('/GetAllRedPack', methods=['get'])
def GetAllRedPack():
    redpack_result = db.session.execute(text("SELECT r.id ,r.`describe`,r.number,r.totalamount ,u.time, er.ID, name, balance FROM redenvelope AS r INNER JOIN user_red AS u INNER JOIN user as er ON u.redid = r.id and u.userid = er.ID;"))
    redpack = redpack_result.fetchall()  # 使用 fetchall() 获取所有结果

    # 打印查询结果
    for item in redpack:
        print(item)

    # 构造返回的 JSON 数据
    data = [{"totalAmount": str(item.totalamount), "id": item.id, "number": item.number, "describe": item.describe,"time":item.time.isoformat(),"ownerID":item.ID,"ownerBalance":str(item.balance),"ownerName":item.name} for item in redpack]

    # 返回 JSON 字符串
    return json.dumps(data)

@app.route('/isGrabed',methods=['post'])
def IsGrabd():
    request_data = request.get_json()
    user_id = int(request_data['user_id'])
    red_id = request_data['red_id']
    print(user_id)
    print(red_id)
    res = db.session.execute(text("select count(*) as c from record where redid = {} and userid = {};".format(red_id,user_id))).first()
    print(res)
    db.session.commit()
    if res.c!=0:
        return dict({"status":"success"})
    else:
        return dict({"status":"false"})
























