import re
import csv
import pymysql
import tomlkit


def is_problematic_content(text: str) -> bool:
    """检查文本是否包含需要特殊处理的内容"""
    if not text:
        return False

    # 1. 检查Emoji
    if re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF]', text):
        return True

    # 2. 检查密集字符画（连续重复字符或模式）
    if re.search(r'(.)\1{10,}', text):  # 连续10个以上相同字符
        return True

    # 3. 检查密集点阵（常见于ASCII艺术）
    if re.search(r'[\.\-_=+*#@]{10,}', text):  # 连续10个以上点阵字符
        return True

    # 4. 检查超长连续空格
    if '          ' in text:  # 10个以上连续空格
        return True

    return False


def clean_content(text: str, max_length: int = 500) -> str:
    """清理问题内容"""
    if not text:
        return ""

    # 1. 截断超长文本
    text = text[:max_length]

    # 2. 替换问题内容
    if is_problematic_content(text):
        return "[内容已过滤]"

    return text


def load_db_config():
    with open('../config/db_config.toml', 'r') as f:
        config = tomlkit.parse(f.read())
    return config['database']


def connect_db():
    config = load_db_config()
    return pymysql.connect(
        host=config['host'],
        port=int(config['port']),
        user=config['user'],
        password=config['password'],
        database=config['database'],
        charset='utf8mb4',  # 关键修改：使用utf8mb4字符集
        cursorclass=pymysql.cursors.DictCursor
    )


def import_recommendations(csv_file):
    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        # Prepare data for insertion
                        data = {
                            'appid': int(row['appid']),
                            'comments': clean_content(row['review_text']),
                            'positive': row['is_recommended'].lower() == 'true',
                            'duration': int(row['playtime_forever']) if row['playtime_forever'] else 0
                        }

                        # Check if the game exists
                        check_sql = "SELECT 1 FROM games WHERE appid = %s"
                        cursor.execute(check_sql, (data['appid'],))
                        if not cursor.fetchone():
                            print(f"Game with appid {data['appid']} not found, skipping recommendation")
                            continue

                        # Build SQL query
                        sql = """
                        INSERT INTO recommendation (appid, comments, positive, duration)
                        VALUES (%s, %s, %s, %s)
                        """

                        cursor.execute(sql, (data['appid'], data['comments'], data['positive'], data['duration']))
                    except Exception as e:
                        print(f"Error processing row: {row}")
                        print(f"Error details: {e}")
                        continue

        connection.commit()
        print(f"Successfully imported {reader.line_num - 1} recommendations")
    finally:
        connection.close()


if __name__ == "__main__":
    csv_file = "../dataset/steam_reviews_data.csv"
    import_recommendations(csv_file)