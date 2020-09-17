import socket
# Here we define the UDP IP address as well as the port number that we have
# already defined in the client python script.
UDP_IP_ADDRESS = ""
UDP_PORT_NO = 5556

serverSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# One difference is that we will have to bind our declared IP address
# and port number to our newly declared serverSock
serverSock.bind((UDP_IP_ADDRESS, UDP_PORT_NO))
while True:
    data, addr = serverSock.recvfrom(1024)
    print ("Message: ", data)
