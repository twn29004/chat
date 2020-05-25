#!/usr/bin/env python
#coding=utf-8

import json
import socket
import threading

# server的TCP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('0.0.0.0',666))
server_socket.listen(120)

# 还需要创建一个server的UDP socket用于存储端口信息
server_udp = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
# 这个操作ok吗？
server_udp.bind(('0.0.0.0',666))

login_map = {"twn":"123456","dzh":"123456"}
socket_map = {}
active_user = []   # 活跃用户的列表
user_ip = {}       # 用户和ip地址的哈希表
udp_addr_map = {}  # 创建用户名和udp的地址端口的对应信息


# keepAlive当一段非常终止连接之后，将其从

# 接受消息的线程，没新来一个连接新建一个线程,将连接的地址作为参数传入函数
def recv(addr):
    while True:
        try:
            try:
                recvive_data = socket_map[addr].recv(1024)
            except Exception as e:
                print(e)
            if recvive_data <= b'0':
                continue
            js = json.loads(recvive_data.decode())
            # 输出消息的类型和消息的地址
            # 登录信息
            if js['type'] == 'login':
                nickname = str(js['nickname'])
                if nickname in active_user:
                    socket_map[addr].send(json.dumps({'login':'fail','errormessage':'已经登录了!!!'}).encode())
                    continue
                if nickname not in login_map.keys() or login_map[nickname] != js['password']:
                    socket_map[addr].send(json.dumps({'login':'fail','errormessage':'用户名或密码错误!!!'}).encode())
                    continue
                # 给他回复一下说明登录成功
                socket_map[addr].send(json.dumps({'login':'success'}).encode())
                # 给其他用户发送登录成功的消息
                for usr in active_user:
                    socket_map[user_ip[usr]].send(json.dumps({'type':'message','message':"{0}登录了".format(nickname)}).encode())
                active_user.append(nickname)
                user_ip[nickname] = addr

            # 下线消息
            elif js['type'] == 'offline':
                # 将和他有关的都清除
                # 需要先关闭socket，不然出问题了
                nickname = js['nickname']
                socket_map[user_ip[nickname]].shutdown(2)
                socket_map[user_ip[nickname]].close()
                active_user.remove(nickname)
                ip = user_ip[nickname]
                socket_map.pop(ip)
                user_ip.pop(nickname)
                # 向其他活跃的用户发送消息
                for user in active_user:
                    socket_map[user_ip[user]].send(json.dumps({'type':'message',
                                                               'message':nickname + "下线了"}).encode())
                # 结束该线程
                break
            # 群发信息
            elif js['type'] == "broadcast":
                message = js['message']
                nickname = js['nickname']
                # 给所有人发消息
                for user in active_user:
                    # 就不用给自己发了
                    if user_ip[user] != addr:
                        socket_map[user_ip[user]].send(json.dumps({'type':'message',
                                                               'message':nickname + ' say to all: ' + message}).encode())
            # 私聊消息
            elif js['type'] == 'private':
                who = js['who']
                nickname = js['nickname']
                message = js['message']
                if who not in active_user:
                    socket_map[addr].send(json.dumps({'type':'message','message':who + " not online,please try later"}).encode())
                else:
                    socket_map[user_ip[who]].send(json.dumps({'type':'message','message':nickname + " say to you: " + message}).encode())

            # 请求发送文件
            elif js['type'] == 'filequest':
                who = js['who']
                # 如果这个人没在活跃用户列表中
                if who not in active_user:
                    socket_map[addr].send(json.dumps({'type':'message',
                                                      'message':who + "not online or not our user"}).encode())
                # 给对方发送消息
                else:
                    js['send_ip'] = udp_addr_map[js['nickname']][0]
                    js['send_port'] = udp_addr_map[js['nickname']][1]
                    socket_map[user_ip[who]].send(json.dumps(js).encode())

            # 文件接受请求
            elif js['type'] == "fileres":
                who = js['who']
                if js['fileres'] == 'yes':
                    js['recv_ip'] = udp_addr_map[js['nickname']][0]
                    js['recv_port'] = udp_addr_map[js['nickname']][1]
                    print(js['nickname'] + "同意接受文件")
                else:
                    print(js['nickname'] + "拒绝接受文件")
                socket_map[user_ip[who]].send(json.dumps(js).encode())

            # 文件传输完毕的标志
            elif js['type'] == 'flag':
                print("这是一个flag")
                socket_map[user_ip[js['who']]].send(json.dumps({'type':'flag'}).encode())
        except Exception as e:
            # 说明连接非正常终止了
            print(addr," 非正常终止了连接")
            socket_map.pop(addr)
            for key in user_ip.keys():
                if user_ip[key] == addr:
                    del user_ip[key]
                    active_user.remove(key)
                    break
            print(active_user)
            break


# 接受各个客户端发来的udp socket
def __udp_recv():
    while True:
        buffer,addr = server_udp.recvfrom(1024)
        js = json.loads(buffer.decode())
        if js['type'] == 'addr':
            print(addr," 成功发送了 udp 消息")
            udp_addr_map[js['nickname']] = addr
            socket_map[user_ip[js['nickname']]].send(json.dumps({'type':'addr'}).encode())


# 一直循环等待客户端连接后创建新的线程接受对应的消息
while True:
    try:
        sock,addr = server_socket.accept()
        print(addr," 连接成功！！！")
        socket_map[addr] = sock
        # 创建线程之后一定记得启动线程
        recv_thread = threading.Thread(target=recv,args=(addr,))
        recv_thread.setDaemon(True)
        recv_thread.start()
        # 创建线程接受各个客户端发送的udp消息
        udp_thread = threading.Thread(target=__udp_recv)
        udp_thread.setDaemon(True)
        udp_thread.start()
    except Exception as e:
        print("what's wrong?")
        print(e)
