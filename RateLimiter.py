""" 
The RateLimiter class is a utility for controlling the execution rate of a loop or recurring function. 
It works by measuring the time taken for each 'cycle' of execution, and then pauses (using time.sleep) 
for the remainder of the desired interval. If a cycle takes longer than the interval, a warning is printed.

The class is initialized with two parameters:
- interval: The desired time interval (in seconds) for each cycle. 
- function_name: An optional name for the function or loop being rate limited, used in warning messages. Defaults to "unnamed function".

The typical usage pattern is as follows:

    limiter = RateLimiter(0.005, function_name="my_function")  # 5 ms per cycle

    while True:
        limiter.start_cycle()

        # Your code here...

        limiter.end_cycle()

At the start of each cycle, call limiter.start_cycle(). At the end of the cycle, call limiter.end_cycle(). 
If the code in the cycle takes longer than the specified interval, a warning message will be printed that 
includes the function name and the specified interval.
"""

import time 
class RateLimiter:
    def __init__(self, interval, function_name="unnamed function", mute = False):
        self.interval = interval
        self.function_name = function_name
        self.start_time = None
        self.mute = mute

    def start_cycle(self):
        self.start_time = time.perf_counter()

    def end_cycle(self):
        if self.start_time is None:
            raise ValueError("Cycle not started. Call start_cycle() before end_cycle().")

        end_time = time.perf_counter()
        elapsed_time = end_time - self.start_time
        remaining_time = self.interval - elapsed_time

        if remaining_time > 0:
            time.sleep(remaining_time)
        else:
            if not self.mute:
                print(f"Warning: Cycle in function '{self.function_name}' took longer {elapsed_time} than the specified interval of {self.interval} seconds")

        self.start_time = None  # reset for the next cycle