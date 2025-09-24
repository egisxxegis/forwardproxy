import proxy_base


def run():
    proxy_base.launch_proxy(
        proxyPort=5173,
        proxyBinding="192.168.1.223",
        proxyForwardTo=("[::1]", 5174),
        name="front",
    )
