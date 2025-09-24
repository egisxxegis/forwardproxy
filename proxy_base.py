#!/usr/bin/python
#
# ForwardProxy
# Port Forwarding Proxy
#
# This is a port-forwarding proxy.
# It connects to another server:port and returns the received data.
# Useful for server-side redirects to local services or resources.
# So you can hide services from public access, but enable controlled
# access through the proxy.
#
# The embedded authentication module protects the proxy itself against
# unauthorized access. This is only an example implementation, which works
# with 2 plain text URL-Parameters. You can us it, how it is (you shouldn't!),
# you can replace it with your own authentication module or you can disable
# the authentication.
#
# Inspired by: https://gist.github.com/darkwave/52842722c0c451807df4
#
# Jann Westphal 02/2020
#
import sys
import time
import socket
import select
import stopper

_print = print
print = _print


class Authenticate:
    #
    # This basic Authenticate implementation works with 2 parameters:
    # - 2 URL-arguments (uname = User name, upass = User Password)
    # Sample-URL: http://192.168.1.17:9800/?uname=admin&upass=test1234

    def __init__(self):
        self.authenticated = False

    def authenticate(self, clientsock, clientaddr):
        path = self.getHTTPPath(clientsock)
        uname = self.getUNameFromHTTPPath(path)
        upass = self.getUPassFromHTTPPath(path)

        if self.verifyUserAccount(uname, upass, clientaddr[0]):
            self.authenticated = True
            print("Client", clientaddr, "authenticated")

        return self.authenticated

    #
    # TODO Re-implement this method, if you use authentication!
    def verifyUserAccount(self, uname, upass, clientIp):
        return uname == "admin" and upass == "test1234"

    # Returns the called URI from http-request
    def getHTTPPath(self, client):
        try:
            req = client.recv(4096)
            path = req.split()[1]
            return path
        except Exception as e:
            print(e)
            return ""

    # Extract argument uname from the called URI
    def getUNameFromHTTPPath(self, path):
        try:
            uname = path[path.rfind("uname=") + 6 : path.rfind("&upass=")]
            return uname
        except Exception as e:
            print(e)
            return ""

    # Extract argument upass from the called URI
    def getUPassFromHTTPPath(self, path):
        try:
            uid = path[path.rfind("upass=") + 6 :]
            return uid
        except Exception as e:
            print(e)
            return ""


class Forward:

    def __init__(self, ip):
        self.forward = socket.socket(
            socket.AF_INET6 if "::" in ip else socket.AF_INET, socket.SOCK_STREAM
        )

    def start(self, host, port):
        try:
            self.forward.connect((host, port))
            print("Forward", [host, port], "connected")
            return self.forward
        except Exception as e:
            print(e)
            return False


class Proxy:

    input_list = []
    channel = {}

    def __init__(
        self,
        host,
        port,
        delay,
        buffer_size,
        stopper_delay,
        proxyAuthentication,
        proxyForwardTo,
        proxyBinding,
    ):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(200)
        self.delay = delay
        self.buffer_size = buffer_size
        self.stopper_delay = stopper_delay
        self.proxyAuthentication = proxyAuthentication
        self.proxyForwardTo = proxyForwardTo
        self.proxyBinding = proxyBinding

    def main_loop(self):
        self.input_list.append(self.server)
        time_checkpoint = time.time()
        time_slept = 0.0
        while 1:
            time.sleep(self.delay)
            ss = select.select
            inputready, outputready, exceptready = ss(
                self.input_list, [], [], self.stopper_delay
            )
            time_slept = time.time() - time_checkpoint
            for self.s in inputready:
                if self.s == self.server:
                    self.on_accept()
                    break

                try:
                    self.data = self.s.recv(self.buffer_size)
                    if len(self.data) == 0:
                        self.on_close()
                        break
                    else:
                        self.on_recv()

                except Exception as e:
                    print(e)
                    self.on_close()
                    break

            if time_slept >= self.stopper_delay:
                if not stopper.is_running_allowed():
                    raise RuntimeError("Stop signal received")
                else:
                    time_slept = 0.0
                    time_checkpoint = time.time()

    def on_accept(self):
        clientsock, clientaddr = self.server.accept()

        authenticated = not self.proxyAuthentication
        if not authenticated:
            authenticated = Authenticate().authenticate(clientsock, clientaddr)
        else:
            print("Connecting client", clientaddr, "without authentication")

        if authenticated:
            forward = Forward(self.proxyForwardTo[0]).start(
                self.proxyForwardTo[0], self.proxyForwardTo[1]
            )
            if forward:
                print("Client", clientaddr, "connected")
                self.input_list.append(clientsock)
                self.input_list.append(forward)
                self.channel[clientsock] = forward
                self.channel[forward] = clientsock
            else:
                print("Can't establish connection with remote server")
                print("Closing connection with client", clientaddr)
                clientsock.close()
        else:
            print("Client", clientaddr, "not authenticated")
            print("Rejecting connection from", clientaddr)
            clientsock.close()

    def on_close(self):
        try:
            print(self.s.getpeername(), "disconnected")
        except Exception as e:
            print(e)
            print("Client closed")

        self.input_list.remove(self.s)
        self.input_list.remove(self.channel[self.s])
        out = self.channel[self.s]
        self.channel[out].close()  # equivalent to do self.s.close()
        self.channel[self.s].close()
        del self.channel[out]
        del self.channel[self.s]

    def on_recv(self):
        data = self.data
        # print data
        self.channel[self.s].send(data)


def launch_proxy(
    delay=0.0001,
    buffer_size=4096,
    # Proxy options
    proxyPort=2024,
    proxyBinding="192.168.1.223",
    proxyForwardTo=("127.0.0.1", 2024),
    proxyAuthentication=False,  # Re-implement authenticate() and verifyUserAccount(), if use!)
    stopper_delay=3,
    name="",
):
    global print
    print = lambda *args, **kwargs: _print(
        (f"[{name}]" if name else "") + str(args[0]), *args[1:], **kwargs
    )
    print(" * ForwardProxy")
    proxy = Proxy(
        proxyBinding,
        proxyPort,
        delay,
        buffer_size,
        stopper_delay,
        proxyAuthentication,
        proxyForwardTo,
        proxyBinding,
    )
    print(" * Listening on: " + str(proxyBinding) + " : " + str(proxyPort))
    print(
        " * Forwarding to: " + str(proxyForwardTo[0]) + " : " + str(proxyForwardTo[1])
    )
    if proxyAuthentication:
        print(" * Authentication: enabled")
    else:
        print(" * Authentication: disabled")
    try:
        proxy.main_loop()
    except (BaseException, RuntimeError):
        print("Stopping server")
        try:
            proxy.on_close()
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    launch_proxy()
