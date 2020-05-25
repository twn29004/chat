#!/usr/bin/env python
# coding=utf-8

import sys
import socket
import threading
import json
import os
from cmd import Cmd
import time


class Client(Cmd):
    buffersize = 1024
    prompt = '>>>'

    def __init__(self, host):
        # message用的socket为tcp
        super().__init__()
        self.__message_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__message_socket.connect(('121.41.129.27', 666))
        # file用的socket为udp
        self.__file_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__nickname = None
        self.__host = host
        self.thread_recv = None
        self.threadisalive = False
        self.server_addr = host

        # 记录udp对应的端口和地址是否已经被服务器记录
        self.udp_addr_flag = False

        # 是否在接收文件
        self.recvfile = False

        # 是否在发送文件
        self.sendfile = False

        self.filesize = None
        self.sendfilesize = 1

        # 接收文件包计数
        self.filecount = 0

        # 接收文件名
        self.filename = None
        # 发送文件名
        self.sendfilename = None
        # 有几个缓冲区
        self.All = 1
        # 发送者
        self.filefrom = None
        # 接收者
        self.fileto = None
        # 接收文件流
        self.file_recv = None
        # 发送文件流
        self.file_send = None
        # 接收文件地址
        self.filefrom_addr = None
        # 发送文件地址
        self.fileto_addr = None

    def __recv_file_thread(self):
        # 如果在接受文件就一直从对应的线程中获取消息
        while self.threadisalive:
            try:
                buffer, addr = self.__file_socket.recvfrom(1024)
                if addr == self.filefrom_addr:
                    self.file_recv.write(buffer)
                    self.filecount += 1
                else:
                    print("[error] 地址不对哦~")
            except Exception as e:
                continue

    def __recv_message_thread(self):
        while self.threadisalive:
            try:
                buffer = self.__message_socket.recv(1024)
                if buffer <= b'0':
                    continue
                try:
                    js = json.loads(buffer.decode())
                    # 接受的是消息
                    if js['type'] == 'message':
                        print(js['message'])
                    # 接受的是文件发送请求
                    elif js['type'] == 'filequest':
                        # 在接受文件的话
                        if self.recvfile:
                            self.__message_socket.send(json.dumps({'type': 'fileres', 'fileres': 'no',
                                                                   'nickname': self.__nickname,
                                                                   'who': js['nickname'],
                                                                   'errormessage': '[error] 正在传送文件'}).encode())
                            continue
                        filename = js['filename']
                        who = js['nickname']
                        self.recvfile = True
                        self.filename = filename
                        self.filefrom = who
                        self.filefrom_addr = (js['send_ip'], js['send_port'])

                        print("[system] ", who, " 请求发送文件，是否接受?")

                    # 文件发送的应答，如果同意则开启文件发送线程
                    elif js['type'] == 'fileres':
                        if js['fileres'] == 'yes':
                            print(js['recv_ip'], js['recv_port'])
                            self.fileto_addr = (js['recv_ip'], js['recv_port'])
                            file_send_thread = threading.Thread(target=self.__send_file_thread)
                            file_send_thread.start()
                            print("[system] 开启文件发送线程")
                        else:
                            print(js['nickname'], js['errormessage'])
                            self.sendfile = False

                    # 如果接受的是文件发送完的标志
                    elif js['type'] == 'flag':
                        self.recvfile = False
                        self.file_recv.close()
                        print("[system] ",self.filename, " 接受完成!!!")

                    # 如果接受到的是服务器关于地址的回复
                    elif js['type'] == 'addr':
                        self.udp_addr_flag = True
                        print("[system] 服务器成功记录了udp的端口")
                except Exception as e:
                    print(e)
            except Exception as e:
                print("[error] 远程主机出现故障，请稍后重试")
                break

    # 发送
    def __send_broadcast_message_thread(self, message):
        self.__message_socket.send(json.dumps({'type': 'broadcast', 'nickname': self.__nickname,
                                               'message': message}).encode())

    # 发送文件的线程
    def __send_file_thread(self):
        filecount = 0
        self.sendfile = True
        print("[system] 发送文件ing")
        self.All = self.sendfilesize / 1024 + 1
        while filecount * 1024 <= self.sendfilesize:
            self.__file_socket.sendto(self.file_send.read(1024), self.fileto_addr)
            filecount += 1
            time.sleep(0.0001)
            print("\r", "[system] 已上传 ", str(filecount / self.All * 100)[0:4], "%", end="", flush=True)
        print('\r')
        self.file_send.close()
        self.sendfile = False
        # 发送完成之后需要给服务器发送一个文件传输完毕的消息
        time.sleep(3)
        self.__message_socket.send(json.dumps({'type': 'flag', 'who': self.fileto}).encode())

    # 发送私聊消息的线程
    def __send_private_message_thread(self, who, message):
        self.__message_socket.send(json.dumps({'type': 'private',
                                               'who': who,
                                               'nickname': self.__nickname,
                                               'message': message}).encode())

    def __send_addr_thread(self):
        while not self.udp_addr_flag:
            self.__file_socket.sendto(json.dumps({"type": "addr", 'nickname': self.__nickname}).encode(),
                                      self.server_addr)
            time.sleep(0.5)
        print("[system] 地址发送线程挂起")

    # 发送离线信息
    def send_exit(self):
        self.__message_socket.send(json.dumps({'type': 'offline',
                                               'nickname': self.__nickname}).encode())
        time.sleep(1)
        self.__message_socket.shutdown(3)
        self.__message_socket.close()

    # 启动命令行工具
    def start(self):
        self.cmdloop()

    # args参数表示命令
    # 登录操作
    def do_login(self, args):
        try:
            nickname = args.split(' ')[0]
            password = args.split(' ')[1]

            self.__message_socket.send(json.dumps({'type': 'login',
                                                   'nickname': nickname,
                                                   'password': password}).encode())
            # 确认登录成功之后再开启接受消息线程
            data = self.__message_socket.recv(1024)
            tmp = json.loads(data)
            # 登录成功
            if tmp['login'] == 'success':
                self.__nickname = nickname
                # 开启消息接受线程
                self.threadisalive = True
                self.thread_recv = threading.Thread(target=self.__recv_message_thread)
                self.thread_recv.setDaemon(True)
                self.thread_recv.start()
                print("[system] 开启消息接受线程")
                # 启动文件接受线程
                file_thread = threading.Thread(target=self.__recv_file_thread)
                file_thread.setDaemon(True)
                file_thread.start()
                print("[system] 开启文件接受线程")
                # 给服务器端发送消息，让服务器知道udp socket对应的端口和地址
                # 服务器还没有给反馈的时候就一直发
                addr_thread = threading.Thread(target=self.__send_addr_thread)
                addr_thread.start()
                print("[system] 向服务器发送udp socket的端口和地址")
                print("[system] 您已成功登录聊天室，可以开始聊天啦~")
            else:
                print(tmp['errormessage'])
        except Exception as e:
            print(e)

    # 退出登录
    def do_exit(self, args):
        self.__message_socket.send(json.dumps({'type': 'offline', 'nickname': self.__nickname}).encode())
        print("[system] 您已成功退出，如需再次登录请重新开启客户端")
        try:
            self.threadisalive = False
            # 当有文件在发送和接受时，禁止退出
            sys.exit(1)
        except Exception as e:
            print(e)

    # 发送群消息
    def do_send(self, args):
        try:
            if self.__nickname == None:
                print("[error] 请先登录后再发送消息")
                return
            message = args
            thread = threading.Thread(target=self.__send_broadcast_message_thread(message))
            thread.start()
        except Exception as e:
            print(e)

    # 发送私聊消息
    def do_sendto(self, args):
        try:
            if self.__nickname == None:
                print("[error] 请先登录后再发送消息")
                return
            who = args.split(' ')[0]
            message = args.split(' ')[1]
            thread = threading.Thread(target=self.__send_private_message_thread, args=(who, message,))
            thread.start()
        except Exception as e:
            print(e)

    def do_sendfile(self, args):
        try:
            who = args.split(' ')[0]
            filepath = args.split(' ')[1]
            filename = filepath.split('\\')[-1]
            # 如果正在发送文件，不允许继续发送
            if self.sendfile:
                print("[error] 你正在发送文件，请稍后再试！！！")
                return
            if not os.path.exists(filepath):
                print("[error] 文件不存在！！！")
                return

            filesize = os.path.getsize(filepath)

            self.sendfile = True
            self.fileto = who
            self.sendfilename = filename
            self.sendfilesize = filesize
            self.file_send = open(filepath, 'rb')

            # 向服务器发送文件发送请求
            self.__message_socket.send(json.dumps({'type': 'filequest',
                                                   'nickname': self.__nickname,
                                                   'filename': self.sendfilename,
                                                   'filesize': self.sendfilesize,
                                                   'who': self.fileto,
                                                   'send_ip': '',
                                                   'send_port': ''}).encode())
        except Exception as e:
            print(e)

    def do_getfile(self, args):
        try:
            if (args == 'yes' or arsg == 'y'):
                self.file_recv = open(self.filename, 'wb')
                self.recvfile = True
                self.__message_socket.send(json.dumps({'type': 'fileres',
                                                       'fileres': 'yes',
                                                       'nickname': self.__nickname,
                                                       'who': self.filefrom,
                                                       'recv_ip': '',
                                                       'recv_port': ''}).encode())
                print("[system] 你同意了接受该文件！！！")
            else:
                self.__message_socket.send(json.dumps({'type': 'fileres',
                                                       'fileres': 'no',
                                                       'nickname': self.__nickname,
                                                       'who': self.filefrom,
                                                       'recv_ip': '',
                                                       'recv_port': ''}).encode())
                self.recvfile = False
                print("[system] 你拒绝了接受该文件！！！")
        except Exception as e:
            print(e)


c = Client(('121.41.129.27', 666))
c.start()
