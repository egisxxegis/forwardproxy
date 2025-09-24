import proxy_base


def run():
    proxy_base.launch_proxy(
        proxyPort=2024, proxyBinding="192.168.1.223", proxyForwardTo=("127.0.0.1", 2024)
    )
