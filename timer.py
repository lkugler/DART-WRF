import time

class Timer:
    """
    A context manager for measuring the execution time of a code block.
    Prints a message before and after the timed block.
    """
    def __init__(self, message="Code block"):
        """
        Initializes the Timer with an optional message.

        Args:
            message (str, optional): The message to print before and after the timed block.
                Defaults to "Code block".
        """
        self.message = message

    def __enter__(self):
        """
        Starts the timer and prints the initial message.
        """
        print(f"{self.message} started.")
        self.start_time = time.perf_counter()
        return self  # Returns self, so you can access the timer object if needed

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Stops the timer, calculates the elapsed time, and prints the final message
        along with the execution time.

        Args:
            exc_type: The type of exception that occurred, if any.
            exc_val: The exception instance, if any.
            exc_tb: A traceback object, if an exception occurred.
        """
        self.end_time = time.perf_counter()
        self.elapsed_time = self.end_time - self.start_time
        print(f"{self.message} finished in {self.elapsed_time:.4f} seconds.")