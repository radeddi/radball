import time
import socket
import datetime
import errno
from datetime import timedelta
import json
from kivy.utils import platform


try:
    if platform == 'android':
        from jnius import autoclass
except:
    platform=""
UDP_IP = ""
UDP_PORT = 5066

sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.settimeout(0.1)
sock.bind((UDP_IP, UDP_PORT))

sock_send = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

last_received=datetime.datetime.now()
json_data=""

client_ip=[]








def str_to_timedelta(time_str):
    try:
        hours, minutes, seconds = time_str.split(':')

        try:
            seconds, microseconds = seconds.split('.')
            microseconds = int(microseconds)
        except ValueError:
            microseconds = 0

        return timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds), microseconds=microseconds)
    except:
        return timedelta(seconds=0)

if __name__ == "__main__":
    
    if platform == 'android':
        Logger = autoclass('java.util.logging.Logger')
        mylogger = Logger.getLogger('MyLogger')
    while 1:
            
        try:
            if platform == 'android':
                mylogger.info("Try")
            #print("hello")
            data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
            
            json_data = json.loads(data)
            
            client_ip = json_data["client_ip"]
            for client in client_ip:
                if platform == 'android':
                    mylogger.info("senden an client "+ str(client))
                try:
                    sock_send.sendto((json.dumps(json_data)+"\n").encode(), (client, 5005))
                except:
                    pass
                if platform == 'android':
                    mylogger.info("gesendet")
            last_received=datetime.datetime.now()
            remaining_time = str_to_timedelta(json_data["rem"])
            
            time.sleep(0.01)
            
        except socket.timeout:
            timeLabel = "0:00"
            if platform == 'android':
                mylogger.info("Except")
            if json_data:
                print(json_data)
                print(remaining_time)
                #mylogger.info(json_data)
                #mylogger.info(remaining_time)
                if remaining_time <= timedelta ( minutes = 0):
                    print("less than 0")
                    remTime = timedelta ( minutes = 0)
                    timeLabel = "0:00"
                else:
                    remTime =  datetime.datetime.now() - last_received + remaining_time
                if json_data["status"] == 0:
                    remTime =  remaining_time
                    if remTime <= timedelta ( minutes = 0):
                        #mylogger.info("1")
                        timeLabel = "0:00"
                        remTime = timedelta ( minutes = 0)
                        #mylogger.info("2")
                    elif remTime < timedelta ( seconds = 10):
                        total_seconds = (remTime.total_seconds())
                        hours, remainder = divmod(total_seconds,60*60)
                        minutes, seconds = divmod(remainder,60)
                  #      seconds, remainder = divmod(remainder,1)
                        timeLabel = '{}:{}'.format("{:02.0f}".format(minutes),"{:04.1f}".format(seconds))
                    else :    
                        total_seconds = int(remTime.total_seconds())
                        hours, remainder = divmod(total_seconds,60*60)
                        minutes, remainder = divmod(remainder,60)
                        seconds, remainder = divmod(remainder,1)
                        timeLabel = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
                elif json_data["status"] == 1:
                    remTime =  last_received + remaining_time - datetime.datetime.now() 
                    if remTime <= timedelta ( minutes = 0):
                        timeLabel = "0:00"
                        remTime = timedelta ( seconds = 0)
                    elif remTime < timedelta ( seconds = 10):
                        total_seconds = (remTime.total_seconds())
                        hours, remainder = divmod(total_seconds,60*60)
                        minutes, seconds = divmod(remainder,60)
                   #     seconds, remainder = divmod(remainder,1)
                        timeLabel = '{}:{}'.format("{:02.0f}".format(minutes),"{:04.1f}".format(seconds))
                    else :    
                        total_seconds = int(remTime.total_seconds())
                        hours, remainder = divmod(total_seconds,60*60)
                        minutes, remainder = divmod(remainder,60)
                        seconds, remainder = divmod(remainder,1)
                        timeLabel = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
                else:
                    pass
                print(timeLabel)
                #mylogger.info("Hello here")
                #mylogger.info(str(timelabel)
                json_data["minutes"] = str(timeLabel.split(":")[0])
                json_data["seconds"] = str(timeLabel.split(":")[1])
                try:
                    for client in client_ip:
                        sock_send.sendto((json.dumps(json_data)+"\n").encode(), (client, 5005))
                except:
                    pass
            time.sleep(0.01)
