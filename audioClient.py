#自主编写，编写人：党茁航+唐文能
import socket
from threading import Thread
import pyaudio
from array import array

HOST = '121.41.129.27'#服务器ip及端口
PORT = 666
BufferSize = 4096 #缓冲区大小

FORMAT=pyaudio.paInt16#数据格式
CHANNELS=2#采样通道
RATE=9000#采样率，本来应该是44100，但是服务器配置较差，采样率较高时传输质量不佳，故降低采样率，需要说话时语速较低
CHUNK=1024

def SendAudio():
    while True:
        data= stream.read(CHUNK) #从声卡中读取信息并发送给服务器
        #client.sendto(data,('127.0.0.1', 666),)
        client.sendto(data,(HOST,PORT),)


def RecieveAudio():
    while True:
        try:
            data,addr= client.recvfrom(4096) #接收服务器转发的数据并写入声卡
            data = recvall(BufferSize)
            stream.write(data)
        except:
            continue

def recvall(size):
    databytes = b''#二进制数据流
    while len(databytes) != size:
        to_read = size - len(databytes) #进行数据的拼接
        if to_read > (4 * CHUNK):
            databytes += client.recv(4 * CHUNK)
        else:
            databytes += client.recv(to_read)
    return databytes

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #创建UDPsocket
audio=pyaudio.PyAudio()#音频采集初始化
stream=audio.open(format=FORMAT,channels=CHANNELS, rate=RATE, input=True, output = True,frames_per_buffer=CHUNK)
RecieveAudioThread = Thread(target=RecieveAudio).start()
SendAudioThread = Thread(target=SendAudio).start()#创建接收与发送线程