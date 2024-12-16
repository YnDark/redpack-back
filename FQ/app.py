import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import random
import matplotlib.pyplot as plt
app = Flask(__name__)
CORS(app)

host = '127.0.0.1'
port = "3306"
username = 'root'
password = 'ydx56HW2004'
database = 'redpack'

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql://{username}:{password}@{host}:{port}/{database}?charset=utf8"
print(app.config['SQLALCHEMY_DATABASE_URI'])

#app config(连接数据库)
db = SQLAlchemy(app)

import threading
import random

# class RedPacketAssignmenter:
#     def __init__(self, total_money, total_persons):
#         self.total_money = total_money
#         self.total_persons = total_persons
#
#     def distribute(self):
#         remaining_money = self.total_money
#         remaining_persons = self.total_persons
#         red_packet_amounts = []
#
#         for i in range(self.total_persons - 1):
#             avg_amount = (remaining_money / remaining_persons) * 2
#             if avg_amount < 0.01:
#                 avg_amount = 0.01
#             current_amount = random.uniform(0.01, avg_amount)
#             current_amount = round(current_amount, 2)
#             red_packet_amounts.append(current_amount)
#             remaining_money -= current_amount
#             remaining_persons -= 1
#
#         last_amount = round(remaining_money, 2)
#         red_packet_amounts.append(last_amount)
#
#         return red_packet_amounts

import threading
import random
import matplotlib.pyplot as plt

class RedPacket:
    lock = threading.Lock()  # 类变量，用于同步

    def __init__(self, money, owner):
        self.money = money
        self.owner = owner
        self.assignedRed_packets = []

    def distribute(self, total_money, total_persons):
        with RedPacket.lock:  # 确保分配红包的代码块是线程安全的
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
            self.assignedRed_packets = red_packet_amounts
            return red_packet_amounts

class User:
    def __init__(self, money, name):
        self.name = name
        self.money = money
        self.Red_packets = []

    def sendPack(self, money, num):
        with RedPacket.lock:  # 确保创建和分配红包的代码块是线程安全的
            if self.money - money < 0:
                print("用户余额不足")
                return None

            newred = RedPacket(money, self.name)
            self.money -= money
            self.Red_packets.append(newred)
            newred.distribute(money, num)
            print("\n{}发了一个红包，总金额为{},个数为{}".format(self.name, money, num))
            print("该红包金额分为：")
            print(newred.assignedRed_packets)
            return newred

    def grabPack(self, redpacket):
        with RedPacket.lock:  # 确保抢红包的代码块是线程安全的
            random.shuffle(redpacket.assignedRed_packets)
            value = redpacket.assignedRed_packets.pop(0)
            self.money += value
            print("{}抢了{}的红包，金额为{}".format(self.name, redpacket.owner, value))
        return value

def user_thread(user, money, num):
    for _ in range(5):  # 每个用户发5次红包
        user.sendPack(money, num)

def grab_thread(user, redpackets):
    for redpacket in redpackets:
        user.grabPack(redpacket)


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
    time = 100000 # 模拟次数


    for _ in range(time):
        distribution = distributeShow(total_money, total_persons)
        distribution_results.extend(distribution)
        print("第{}轮分配金额".format(time))
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

# 测试串行抢红包
def testUserGrap():
    user = User(100,"杨定鑫")
    user2 = User(200,"张富钧")
    user2.sendPack(100,10)
    user.grabPack(user2.Red_packets[0])

# 测试多线程
def testMultiThreading():
    users = [User(1000, "用户{}".format(i)) for i in range(5)]  # 创建5个用户
    threads = []

    # 创建发送红包的线程
    for user in users:
        thread = threading.Thread(target=user_thread, args=(user, 100, 10))
        threads.append(thread)
        thread.start()

    # 等待所有发送红包的线程完成
    for thread in threads:
        thread.join()

    # 收集所有红包
    redpackets = [user.Red_packets[0] for user in users]

    # 创建抢红包的线程
    for user in users:
        thread = threading.Thread(target=grab_thread, args=(user, redpackets))
        threads.append(thread)
        thread.start()

    # 等待所有抢红包的线程完成
    for thread in threads:
        thread.join()

test()
testUserGrap()
testMultiThreading()

# @app.route('/assignment')
# def assignment():
    # total_money = request.args.get('total_money')
    # total_persons = request.args.get('total_money')
    # assignmenter = RedPacketAssignmenter(total_money, total_persons)
    # red_packet = assignmenter.distribute()
    # return jsonify({"redpacks": red_packet})

# @app.route('/getNowPacket')
# def getNowPacket():
#     return jsonify({"redpacks": red_packet})
# @app.route('/grab')
# def grab():
#
#     return jsonify({"redpacks": red_packet})



























