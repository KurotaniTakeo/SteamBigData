# 导入部分
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, regexp_replace, split, array_contains, lit, rand
from database import Database  # 从app.py导入Database类
from functools import reduce
import random
from pyspark.sql.functions import rand

# 创建spraksession数据处理入口
spark = SparkSession.builder.appName("SteamUserSimilarityRecommendation").getOrCreate()

# 加载游戏数据
df_raw = spark.read.option("header", "true").csv("steam_games.csv")
# 游戏价格处理 free->0 去掉美元符号
df = df_raw.withColumn("price_num",
                       when(col("price") == "Free", 0.0).otherwise(regexp_replace("price", "\\$", "").cast("double")))
# genres和catagories处理 split函数分割成数组格式
df = df.withColumn("genres_array", split(regexp_replace("genres", r"[\[\]']", ""), r",\s*"))
df = df.withColumn("categories_array", split(regexp_replace("categories", r"[\[\]']", ""), r",\s*"))


# 获取用户偏好数据（从 preferences 表）
def get_user_preferences():
    with Database.cursor(dict_cursor=True) as cursor:
        cursor.execute("SELECT user_id, prefer, value FROM preferences")
        raw = cursor.fetchall()

    user_prefs = {}
    for row in raw:
        uid = row["user_id"]
        if uid not in user_prefs:
            user_prefs[uid] = {"genres": [], "categories": [], "platforms": [], "price": "medium"}  # default
        if row["prefer"] == "price":
            user_prefs[uid]["price"] = row["value"]
        elif row["prefer"] == "genre":
            user_prefs[uid]["genres"].append(row["value"])
        elif row["prefer"] == "category":
            user_prefs[uid]["categories"].append(row["value"])
        elif row["prefer"] == "platform":
            user_prefs[uid]["platforms"].append(row["value"])
        else:
            user_prefs[uid][row["prefer"]].append(row["value"])
    return user_prefs


# 评分函数
def genre_score_expr(genres_array, user_genres):
    return reduce(lambda a, b: a + b,
                  [when(array_contains(genres_array, g), 2).otherwise(0) for g in user_genres]) if user_genres else lit(
        0)


def category_score_expr(cat_array, user_categories):
    return reduce(lambda a, b: a + b, [when(array_contains(cat_array, c), 2).otherwise(0) for c in
                                       user_categories]) if user_categories else lit(0)


def platform_score_expr(user_platforms):
    valid_platform_cols = {"platforms_windows", "platforms_mac", "platforms_linux"}
    if not user_platforms:
        return lit(0)
    return reduce(lambda a, b: a + b, [
        when(col(p) == "True", 3).otherwise(0)
        for p in user_platforms if p in valid_platform_cols
    ], lit(0))


def price_score_expr(price_col, price_pref):
    if price_pref == "low":
        return when(price_col <= 5, 2).otherwise(0)
    elif price_pref == "medium":
        return when((price_col > 5) & (price_col <= 15), 2).otherwise(0)
    else:
        return when(price_col > 15, 2).otherwise(0)


# 相似度计算（jaccard）
def jaccard_similarity(set1, set2):
    if not set1 or not set2:
        return 0
    return len(set(set1) & set(set2)) / len(set(set1) | set(set2))


def get_existing_recommendations():
    with Database.cursor(dict_cursor=True) as cursor:
        cursor.execute("SELECT uid, recommend_games FROM users")
        rows = cursor.fetchall()

    existing = {}
    for row in rows:
        uid = row['uid']
        existing[uid] = set(map(int, row['recommend_games'].split(','))) if row['recommend_games'] else set()
    return existing


# 主推荐函数
def generate_recommendations(refresh=False):
    user_prefs = get_user_preferences()
    existing_rec = get_existing_recommendations() if refresh else {}

    for uid, prefs in user_prefs.items():
        already = existing_rec.get(uid, set())
        df_filtered = df.filter(~col("appid").isin(already)) if refresh else df

        df_scored = df_filtered.withColumn("genre_score", genre_score_expr(col("genres_array"), prefs["genres"])) \
            .withColumn("category_score", category_score_expr(col("categories_array"), prefs["categories"])) \
            .withColumn("platform_score", platform_score_expr(prefs["platforms"])) \
            .withColumn("price_score", price_score_expr(col("price_num"), prefs["price"])) \
            .withColumn("total_score",
                        col("genre_score") + col("category_score") + col("platform_score") + col("price_score"))

        top7 = [row["appid"] for row in df_scored.orderBy(col("total_score").desc()).limit(7).select("appid").collect()]

        similarities = []
        for other_uid, other_prefs in user_prefs.items():
            if other_uid == uid:
                continue
            sim = (
                    jaccard_similarity(prefs["genres"], other_prefs["genres"]) +
                    jaccard_similarity(prefs["categories"], other_prefs["categories"]) +
                    jaccard_similarity(prefs["platforms"], other_prefs["platforms"])
            )
            similarities.append((other_uid, sim))
        similarities.sort(key=lambda x: -x[1])
        similar_users = [u[0] for u in similarities[:3]]

        similar_game_ids = set()
        for u in similar_users:
            similar_df = df_filtered.withColumn("genre_score",
                                                genre_score_expr(col("genres_array"), user_prefs[u]["genres"])) \
                .withColumn("category_score", category_score_expr(col("categories_array"), user_prefs[u]["categories"])) \
                .withColumn("platform_score", platform_score_expr(user_prefs[u]["platforms"])) \
                .withColumn("price_score", price_score_expr(col("price_num"), user_prefs[u]["price"])) \
                .withColumn("total_score",
                            col("genre_score") + col("category_score") + col("platform_score") + col("price_score"))
            games = [r["appid"] for r in
                     similar_df.orderBy(col("total_score").desc()).select("appid").limit(10).collect()]
            similar_game_ids.update(games)
        top3_similar = list(similar_game_ids - set(top7))[:3]

        # 推荐热度排序时将 'N/A' 转为 0
        rec_score_col = when(col("recommendations").isNull(), 0) \
            .when(col("recommendations") == "N/A", 0) \
            .otherwise(col("recommendations").cast("int"))

        top_hot_games = df_filtered \
            .withColumn("rec_score", rec_score_col) \
            .orderBy(col("rec_score").desc()) \
            .select("appid") \
            .limit(50)

        top3_hot = [row["appid"] for row in top_hot_games.orderBy(rand()).limit(3).collect()]

        final_recommend = top7 + top3_similar + top3_hot
        save_recommendation_to_db(uid, final_recommend)
        print(f"为用户 {uid} 生成新推荐：{final_recommend}")


# 更新到数据库
def save_recommendation_to_db(user_id, appid_list):
    with Database.cursor() as cursor:
        appid_str = ",".join(map(str, appid_list))
        cursor.execute("UPDATE users SET recommend_games=%s WHERE uid=%s", (appid_str, user_id))


# 启动推荐流程
if __name__ == "__main__":
    generate_recommendations()
