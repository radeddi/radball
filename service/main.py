import time
import socket
import datetime
import errno


MCAST_GRP = '224.1.1.1'
MCAST_PORT = 5007

if __name__ == "__main__":
  while 1:
    try:
      sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      # optional - reuse address / sockets
      sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
      sock.setblocking(0)
      # bind to host "" (any) and port 6666
      sock.bind(("", 5555))
      break
    except:
      pass


      
  def send_udp_test():
    while 1:#for i in ["192.168.1.6"]:
      try:
        msg, addr = sock.recvfrom(1024)
        print ("%s: %s" % (addr, msg))
      except socket.error as e:
          err = e.args[0]
          if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
              time.sleep(.1)
              #print ('No data available')
              continue
          else:
              # a "real" error occurred
              print (e)
              sys.exit(1)
      else:
          # got a message, do something :)
          print("message")
          try:
            sock.sendto(msg, ("192.168.1.5", 6666))
          except:
            pass
          

  send_udp_test()
