class Counter:
    thread_count = 0

    @staticmethod
    def add_count():
        Counter.thread_count += 1
        print('Count added: ' + str(Counter.thread_count))

    @staticmethod
    def remove_count():
        Counter.thread_count -= 1
        print('Count sub: ' + str(Counter.thread_count))
