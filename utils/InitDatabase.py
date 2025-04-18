import pymysql
import tomlkit
from typing import Dict, List, Tuple


# 从配置文件读取数据库连接信息
def load_db_config() -> Dict:
    with open('../config/db_config.toml', 'r') as f:
        config = tomlkit.load(f)
    return config['database']


# 获取数据库连接
def get_db_connection(config: Dict) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=config['host'],
        port=int(config['port']),
        user=config['user'],
        password=config['password'],
        database=config['database'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


# 检查表结构是否符合预期
def check_table_structure(conn: pymysql.connections.Connection, table_name: str, expected_columns: List[Tuple]) -> bool:
    with conn.cursor() as cursor:
        cursor.execute(f"DESCRIBE {table_name}")
        existing_columns = cursor.fetchall()

        if len(existing_columns) != len(expected_columns):
            return False

        for existing_col, expected_col in zip(existing_columns, expected_columns):
            # 检查字段名、类型、是否允许NULL、键类型等
            if (existing_col['Field'].lower() != expected_col[0].lower() or
                    not existing_col['Type'].lower().startswith(expected_col[1].lower()) or
                    (existing_col['Null'] == 'YES') != (expected_col[2] == 'YES') or
                    existing_col['Key'].lower() != expected_col[3].lower()):
                return False

            # 检查默认值
            if expected_col[4] is not None:
                if existing_col['Default'] != expected_col[4]:
                    return False

        return True


# 创建或修改表结构
def setup_table(conn: pymysql.connections.Connection, table_name: str, create_sql: str):
    with conn.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        cursor.execute(create_sql)
    conn.commit()


# 主函数
def main():
    # 加载配置
    config = load_db_config()

    # 定义预期的表结构
    expected_tables = {
        'games': (
            ('appid', 'int', 'NO', 'PRI', None),
            ('name', 'varchar(255)', 'YES', '', None),
            ('price', 'varchar(50)', 'YES', '', None),
            ('recommendations', 'int', 'YES', '', None),
            ('metacritic', 'varchar(10)', 'YES', '', None),
            ('controller_support', 'varchar(50)', 'YES', '', None),
            ('developers', 'text', 'YES', '', None),
            ('publishers', 'text', 'YES', '', None),
            ('platforms_windows', 'tinyint(1)', 'YES', '', None),
            ('platforms_mac', 'tinyint(1)', 'YES', '', None),
            ('platforms_linux', 'tinyint(1)', 'YES', '', None),
            ('release_date', 'varchar(50)', 'YES', '', None),
            ('minimum_req', 'text', 'YES', '', None),
            ('recommended_req', 'text', 'YES', '', None),
            ('categories', 'text', 'YES', '', None),
            ('genres', 'text', 'YES', '', None),
            ('header_image', 'text', 'YES', '', None)
        ),
        'users': (
            ('uid', 'int', 'NO', 'PRI', None),
            ('mail', 'varchar(255)', 'NO', 'UNI', None),
            ('password', 'varchar(255)', 'NO', '', None),
            ('user_name', 'varchar(50)', 'NO', '', None),
            ('age', 'int', 'YES', '', None),
            ('gender', 'varchar(10)', 'YES', '', None),
            ('recommend_games', 'varchar(255)', 'YES', '', None),
            ('created_at', 'timestamp', 'YES', '', 'CURRENT_TIMESTAMP'),
            ('updated_at', 'timestamp', 'YES', '', 'CURRENT_TIMESTAMP')
        ),
        'recommendation': (
            ('r_id', 'int', 'NO', 'PRI', None),
            ('appid', 'int', 'YES', 'MUL', None),
            ('comments', 'text', 'YES', '', None),
            ('positive', 'tinyint(1)', 'YES', '', None),
            ('duration', 'int', 'YES', '', None)
        ),
        'preferences': (
            ('p_id', 'int', 'NO', 'PRI', None),
            ('user_id', 'int', 'NO', 'MUL', None),
            ('prefer', 'varchar(50)', 'YES', '', None),
            ('value', 'varchar(100)', 'YES', '', None)
        )
    }

    # 定义创建表的SQL语句
    create_sqls = {
        'games': """
                 CREATE TABLE games
                 (
                     appid              INT PRIMARY KEY,
                     name               VARCHAR(255),
                     price              VARCHAR(50),
                     recommendations    INT,
                     metacritic         VARCHAR(10),
                     controller_support VARCHAR(50),
                     developers         TEXT,
                     publishers         TEXT,
                     platforms_windows  BOOLEAN,
                     platforms_mac      BOOLEAN,
                     platforms_linux    BOOLEAN,
                     release_date       VARCHAR(50),
                     minimum_req        TEXT,
                     recommended_req    TEXT,
                     categories         TEXT,
                     genres             TEXT,
                     header_image       TEXT
                 )
                 """,
        'users': """
                 CREATE TABLE users
                 (
                     uid             INT AUTO_INCREMENT PRIMARY KEY,
                     mail            VARCHAR(255) NOT NULL UNIQUE,
                     password        VARCHAR(255) NOT NULL,
                     user_name       VARCHAR(50)  NOT NULL,
                     age             INT,
                     gender          VARCHAR(10),
                     recommend_games VARCHAR(255),
                     created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                 )
                 """,
        'recommendation': """
                          CREATE TABLE recommendation
                          (
                              r_id     INT AUTO_INCREMENT PRIMARY KEY,
                              appid    INT,
                              comments TEXT,
                              positive BOOLEAN,
                              duration INT,
                              FOREIGN KEY (appid) REFERENCES games (appid) ON DELETE CASCADE
                          )
                          """,
        'preferences': """
                       CREATE TABLE preferences
                       (
                           p_id    INT AUTO_INCREMENT PRIMARY KEY,
                           user_id INT NOT NULL,
                           prefer  VARCHAR(50),
                           value   VARCHAR(100),
                           UNIQUE (user_id, prefer, value),
                           FOREIGN KEY (user_id) REFERENCES users (uid) ON DELETE CASCADE
                       )
                       """
    }

    try:
        # 获取数据库连接
        conn = get_db_connection(config)

        # 检查并创建/修改每个表
        for table_name in expected_tables.keys():
            with conn.cursor() as cursor:
                # 检查表是否存在
                cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                table_exists = cursor.fetchone() is not None

                if table_exists:
                    # 检查表结构是否符合预期
                    if check_table_structure(conn, table_name, expected_tables[table_name]):
                        print(f"表 {table_name} 结构符合预期，无需修改")
                        continue
                    else:
                        print(f"表 {table_name} 结构不符合预期，将重新创建")
                else:
                    print(f"表 {table_name} 不存在，将创建")

                # 创建或修改表
                setup_table(conn, table_name, create_sqls[table_name])
                print(f"表 {table_name} 创建/修改完成")

        print("数据库初始化完成")

    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()


if __name__ == '__main__':
    main()
