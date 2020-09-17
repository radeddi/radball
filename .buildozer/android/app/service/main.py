import sys, os; sys.path = [os.path.join(os.getcwd(),"..", "_applibs")] + sys.path
import time
import socket
import datetime

MCAST_GRP = '224.1.1.1'
MCAST_PORT = 5007

if __name__ == "__main__":
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	# optional - reuse address / sockets
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
	sock.setblocking(0)
	# bind to host "" (any) and port 6666
	sock.bind(("", 5555))


	
		
	def send_udp_test():
		while 1:#for i in ["192.168.1.6"]:
			
			try:
				sock.sendto(bytes(str(datetime.datetime.now()),"UTF-8"), ("255.255.255.255", 5555))
				print("sent")
			except Exception as Error:
				print(Error)
				print("network error")
			time.sleep(0.1)

	send_udp_test()
