import os
from redis import Redis
from rq import Worker, Queue, Connection


def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_conn = Redis.from_url(redis_url)
    with Connection(redis_conn):
        worker = Worker([Queue("ownership")])
        worker.work()


if __name__ == "__main__":
    main()
