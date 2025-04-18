import csv
import pymysql
import tomlkit
from datetime import datetime
import json


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
        cursorclass=pymysql.cursors.DictCursor
    )


def parse_price(price_str):
    if price_str.lower() == 'free':
        return '0.00'
    if price_str.startswith('$'):
        return price_str[1:]
    return price_str


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%b %d, %Y").strftime("%Y-%m-%d")
    except:
        return date_str


def parse_requirements(req_str):
    if not req_str or req_str == '{}':
        return None
    try:
        return json.dumps(eval(req_str))
    except:
        return req_str


def parse_list_field(list_str):
    if not list_str or list_str == '[]':
        return None
    try:
        return ', '.join(eval(list_str))
    except:
        return list_str


def import_games(csv_file):
    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Prepare data for insertion
                    data = {
                        'appid': int(row['appid']),
                        'name': row['name'],
                        'price': parse_price(row['price']),
                        'recommendations': int(float(row['recommendations'])) if row['recommendations'] else None,
                        'metacritic': row['metacritic'] if row['metacritic'] else None,
                        'controller_support': row['controller_support'] if row['controller_support'] else None,
                        'developers': row['developers'],
                        'publishers': row['publishers'],
                        'platforms_windows': bool(row['platforms_windows']),
                        'platforms_mac': bool(row['platforms_mac']),
                        'platforms_linux': bool(row['platforms_linux']),
                        'release_date': parse_date(row['release_date']),
                        'minimum_req': parse_requirements(row['minimum_req']),
                        'recommended_req': parse_requirements(row['recommended_req']),
                        'categories': parse_list_field(row['categories']),
                        'genres': parse_list_field(row['genres']),
                        'header_image': row['header_image']
                    }

                    # Build SQL query
                    columns = ', '.join(data.keys())
                    placeholders = ', '.join(['%s'] * len(data))
                    sql = f"INSERT INTO games ({columns}) VALUES ({placeholders})"

                    try:
                        cursor.execute(sql, tuple(data.values()))
                    except pymysql.err.IntegrityError:
                        print(f"Duplicate entry for appid {data['appid']}, skipping...")
                        continue

        connection.commit()
        print(f"Successfully imported {reader.line_num - 1} games")
    finally:
        connection.close()


if __name__ == "__main__":
    csv_file = "../dataset/steam_games_data.csv"  # 替换为实际的games.csv文件路径
    import_games(csv_file)