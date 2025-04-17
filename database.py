# database.py 内容
from pathlib import Path
import tomlkit
from contextlib import contextmanager
from pymysql import Connection
from pymysql.cursors import DictCursor


class Database:
    _config = None

    @classmethod
    def _load_config(cls):
        if cls._config is None:
            with open("config/db_config.toml", "rb") as f:
                cls._config = tomlkit.load(f)['database']
        return cls._config

    @classmethod
    @contextmanager
    def connection(cls):
        db_config = cls._load_config()
        conn = Connection(
            host=db_config['host'],
            port=int(db_config['port']),
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        try:
            yield conn
        finally:
            conn.close()

    @classmethod
    @contextmanager
    def cursor(cls, dict_cursor=False):
        with cls.connection() as conn:
            cursor = conn.cursor(DictCursor if dict_cursor else None)
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
