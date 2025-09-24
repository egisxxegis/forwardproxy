import sys
import time
import stopper
import proxy_backend
import proxy_frontend
from multiprocessing import Process
from datetime import datetime


def main():
    try:
        print("Is running already? ", stopper.is_running_allowed())
        stopper.allow_running()
        print("Running just got allowed.")
        # spawn process
        backend_process = Process(target=proxy_backend.run)
        frontend_process = Process(target=proxy_frontend.run)
        backend_process.start()
        frontend_process.start()
        while backend_process.is_alive() or frontend_process.is_alive():
            time.sleep(30)
    except (BaseException, Exception) as ex:
        print(f"Error: {ex=}")
        seconds_join = 10
        stopper.disallow_running()
        dt_start_stop = datetime.now()
        print(
            f"Disallowing running and waiting for processes to finish in {seconds_join} seconds."
        )
        backend_process.join(seconds_join)
        frontend_process.join(min((datetime.now() - dt_start_stop).total_seconds(), 1))
        joined_in_s = (datetime.now() - dt_start_stop).total_seconds()
        print(f"Bye, processes joined in {joined_in_s} seconds.")
        sys.exit(1)


if __name__ == "__main__":
    main()
