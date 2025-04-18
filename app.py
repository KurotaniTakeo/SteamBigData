"""

"""

import ast
import base64
import io
import re
import jieba
import jieba.analyse
import numpy as np

from pathlib import Path
from PIL import Image
from decouple import config
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from wordcloud import WordCloud
from database import Database

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = config('SECRET_KEY')


@app.route('/')
def index():
    user_name = session.get('user_name')
    return render_template('index.html', user_name=user_name)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mail = request.form['mail']
        password = request.form['password']

        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE mail = %s AND password = %s",
                (mail, password)
            )
            user = cursor.fetchone()

        if user:
            session['user_name'] = user[3]
            session['user_id'] = user[0]
            flash('登录成功！', 'success')
            return render_template('login.html', user_name=user[3], user_id=user[0], delay_redirect=True)

        flash('邮箱或密码错误！', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_name', None)
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        form_data = (
            request.form['mail'],
            request.form['password'],
            request.form['user_name'],
            request.form['age'],
            request.form['gender'],
        )

        query = """
                INSERT INTO users
                    (mail, password, user_name, age, gender)
                VALUES (%s, %s, %s, %s, %s) \
                """

        try:
            with Database.cursor() as cursor:
                cursor.execute(query, form_data)
            flash('注册成功！', 'success')
        except Exception as e:
            flash(f'注册失败：{str(e)}', 'danger')

        return redirect(url_for('register'))

    return render_template("register.html")


# 偏好完善度
def get_preference_completeness(user_id):
    prefer_types = {"price", "genre", "category", "platform"}
    user_pref_types = set()

    with Database.cursor() as cursor:
        cursor.execute("SELECT DISTINCT prefer FROM preferences WHERE user_id = %s", (user_id,))
        rows = cursor.fetchall()
        user_pref_types = {row[0] for row in rows}

    completeness = len(user_pref_types) / len(prefer_types) * 100
    return round(completeness)


# 用于资料完善度
def get_profile_completeness(user_id):
    with Database.cursor() as cursor:
        cursor.execute("SELECT age, gender FROM users WHERE uid = %s", (user_id,))
        row = cursor.fetchone()

    age = row[0]
    gender = row[1]

    # 年龄必须大于 0 且非空，性别必须是非空字符串
    age_filled = age is not None and age > 0
    gender_filled = gender is not None and gender.strip() != ""

    filled = sum([age_filled, gender_filled])
    completeness = filled / 2 * 100
    return round(completeness)


# 用于游戏数统计
def get_total_game_count():
    with Database.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM games")
        return cursor.fetchone()[0]


# 用于注册人数统计
def get_total_user_count():
    with Database.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]


@app.route('/user')
def user():
    user_name = session.get('user_name')
    user_id = session.get('user_id')

    pref_score = get_preference_completeness(user_id)
    profile_score = get_profile_completeness(user_id)
    game_count = get_total_game_count()
    user_count = get_total_user_count()

    return render_template(
        "user.html",
        user_name=user_name,
        user_id=user_id,
        pref_score=pref_score,
        profile_score=profile_score,
        game_count=game_count,
        user_count=user_count
    )


@app.route('/preference')
def preference():
    user_name = session.get('user_name')
    user_id = session.get('user_id')

    # 初始化前端需要的偏好格式
    preferences = {
        'genre': [],
        'category': [],
        'price': [],
        'platform': []
    }

    # 反向映射英文 ➜ 中文（只对 genre 和 category）
    reverse_translations = {
        'genre': {v: k for k, v in translations['genre'].items()},
        'category': {v: k for k, v in translations['category'].items()}
    }

    if user_id:
        query = "SELECT prefer, value FROM preferences WHERE user_id = %s"
        with Database.cursor() as cursor:
            cursor.execute(query, (user_id,))
            for prefer_type, value in cursor.fetchall():
                if prefer_type in preferences:
                    if prefer_type in reverse_translations:
                        # 翻译为中文后存入
                        cn_value = reverse_translations[prefer_type].get(value, value)
                        preferences[prefer_type].append(cn_value)
                    else:
                        # price 和 platform 保持原样
                        preferences[prefer_type].append(value)

    return render_template("preference.html", user_name=user_name, user_id=user_id, preferences=preferences)


@app.route('/SDP')
def SDP():
    user_name = session.get('user_name')
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录，无法使用SDP'}), 403
    return render_template("SDP.html", user_name=user_name, user_id=user_id)


def smart_parse_list(text):
    if not text:
        return []
    if isinstance(text, list):
        return text
    try:
        return ast.literal_eval(text)
    except:
        return [i.strip(" []'\"") for i in re.split(r"[,\n]", text) if i.strip()]


@app.route('/SRS', methods=['GET'])
def SRS():
    user_name = session.get('user_name')
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录，无法使用SRS'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    datalist = []
    total_pages = 1

    try:
        with Database.cursor() as cursor:
            # 获取该用户的推荐游戏 appid 字符串
            cursor.execute("SELECT recommend_games FROM users WHERE uid = %s", (user_id,))
            result = cursor.fetchone()
            if not result or not result[0]:
                return render_template("SRS.html", games=[], page=1, total_pages=1, page_numbers=[1],
                                       user_name=user_name, user_id=user_id)

            appid_list = result[0].split(",")  # 字符串转数组
            appid_list = list(dict.fromkeys(appid_list))  # 去重（可选）
            appid_list = [int(i) for i in appid_list if i.isdigit()]  # 转成整数

            # 分页处理推荐游戏
            total_games = len(appid_list)
            total_pages = (total_games + per_page - 1) // per_page
            appids_this_page = appid_list[offset: offset + per_page]

            if not appids_this_page:
                return render_template("SRS.html", games=[], page=page, total_pages=total_pages,
                                       page_numbers=[page], user_name=user_name, user_id=user_id)

            # 查询当前页的游戏详情
            placeholders = ','.join(['%s'] * len(appids_this_page))
            query = f"SELECT * FROM games WHERE appid IN ({placeholders})"
            cursor.execute(query, appids_this_page)
            rows = cursor.fetchall()

            for item in rows:
                item = list(item)
                item[14] = smart_parse_list(item[14])
                item[15] = smart_parse_list(item[15])
                datalist.append(item)

    except Exception as e:
        return jsonify({'error': f'数据库查询失败：{str(e)}'}), 500

    # 分页按钮逻辑
    if total_pages <= 10:
        page_numbers = list(range(1, total_pages + 1))
    else:
        if page <= 5:
            page_numbers = [1, 2, 3, 4, 5, 6, '...', total_pages]
        elif page >= total_pages - 4:
            page_numbers = [1, '...', total_pages - 5, total_pages - 4, total_pages - 3, total_pages - 2,
                            total_pages - 1, total_pages]
        else:
            page_numbers = [1, '...', page - 1, page, page + 1, '...', total_pages]

    reverse_translations = {
        "category": {v: k for k, v in translations["category"].items()},
        "genre": {v: k for k, v in translations["genre"].items()},
    }
    return render_template("SRS.html",
                           games=datalist,
                           page=page,
                           total_pages=total_pages,
                           page_numbers=page_numbers,
                           user_name=user_name,
                           user_id=user_id,
                           reverse_translations=reverse_translations)


from recommendations import generate_recommendations


# 刷新偏好
@app.route('/refresh_recommendations', methods=['POST'])
def refresh_recommendations():
    try:
        generate_recommendations(refresh=True)
        return jsonify({"status": "success", "message": "推荐列表已刷新!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# 全部游戏
@app.route('/show_all_games', methods=['GET'])
def show_all_games():
    # 统一风格：获取 session 参数部分抽离
    user_name = session.get('user_name')
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录，无法使用'}), 403

    # 统一风格：获取分页参数部分
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    datalist = []
    total_pages = 1

    # 统一风格：数据库查询逻辑放入 try 块中
    try:
        with Database.cursor() as cursor:
            # 查询总数 & 页码
            cursor.execute("SELECT COUNT(*) FROM games")
            total_games = cursor.fetchone()[0]
            total_pages = (total_games + per_page - 1) // per_page

            # 查询本页数据
            query = "SELECT * FROM games LIMIT %s OFFSET %s"
            cursor.execute(query, (per_page, offset))
            rows = cursor.fetchall()
        for item in rows:
            item = list(item)
            item[14] = smart_parse_list(item[14])
            item[15] = smart_parse_list(item[15])
            datalist.append(item)

    except Exception as e:
        return jsonify({'error': f'数据库查询失败：{str(e)}'}), 500

    finally:
        if 'cur' in locals():
            cursor.close()
        if 'con' in locals():
            cursor.close()

    # 统一风格：分页页码列表
    if total_pages <= 10:
        page_numbers = list(range(1, total_pages + 1))
    else:
        if page <= 5:
            page_numbers = [1, 2, 3, 4, 5, 6, '...', total_pages]
        elif page >= total_pages - 4:
            page_numbers = [1, '...', total_pages - 5, total_pages - 4, total_pages - 3, total_pages - 2,
                            total_pages - 1, total_pages]
        else:
            page_numbers = [1, '...', page - 1, page, page + 1, '...', total_pages]

    reverse_translations = {
        "category": {v: k for k, v in translations["category"].items()},
        "genre": {v: k for k, v in translations["genre"].items()},
    }
    return render_template("show_all_games.html",
                           games=datalist,
                           page=page,
                           total_pages=total_pages,
                           page_numbers=page_numbers,
                           user_name=user_name,
                           user_id=user_id,
                           reverse_translations=reverse_translations)


@app.route('/price_distribution')
def price_distribution():
    user_name = session.get('user_name')
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录，无法使用SDP'}), 403
    return render_template("steam_price_distribution_line.html", user_name=user_name, user_id=user_id)


@app.route('/game_platform')
def game_platform():
    user_name = session.get('user_name')
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录，无法使用SDP'}), 403
    return render_template("game_platform_distribution.html", user_name=user_name, user_id=user_id)


@app.route('/game_release')
def game_release():
    user_name = session.get('user_name')
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录，无法使用SDP'}), 403
    return render_template("game_release_trend.html", user_name=user_name, user_id=user_id)


@app.route('/recommend_bar')
def recommend_bar():
    user_name = session.get('user_name')
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录，无法使用SDP'}), 403
    return render_template("recommendation_bar_chart.html", user_name=user_name, user_id=user_id)


@app.route('/change')
def change():
    user_name = session.get('user_name')
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录，无法使用修改用户信息'}), 403
    return render_template("change.html", user_name=user_name, user_id=user_id)


@app.route('/update-user-info', methods=['POST'])
def update_user_info():
    user_id = session.get('user_id')
    if not user_id:
        flash('请先登录后再修改资料', 'danger')
        return redirect(url_for('login'))

    mail = request.form.get('mail')
    password = request.form.get('password')  # 可选
    user_name = request.form.get('user_name')
    age = request.form.get('age')
    gender = request.form.get('gender')

    try:
        with Database.cursor() as cursor:
            # 可根据 password 是否为空来判断是否更新
            if password:
                cursor.execute(
                    "UPDATE users SET mail=%s, password=%s, user_name=%s, age=%s, gender=%s WHERE uid=%s",
                    (mail, password, user_name, age, gender, user_id)
                )
            else:
                cursor.execute(
                    "UPDATE users SET mail=%s, user_name=%s, age=%s, gender=%s WHERE uid=%s",
                    (mail, user_name, age, gender, user_id)
                )
        flash('资料修改成功！', 'success')
        # 更新 session 中的 user_name
        session['user_name'] = user_name
    except Exception as e:
        print("资料更新出错:", e)
        flash('修改失败，请稍后再试。', 'danger')

    return redirect(url_for('user'))


translations = {
    "category": {
        "提供字幕": "Captions available",
        "合作模式": "Co-op",
        "提供解说": "Commentary available",
        "跨平台多人游戏": "Cross-Platform Multiplayer",
        "家庭共享": "Family Sharing",
        "完全支持手柄": "Full controller support",
        "支持 HDR": "HDR available",
        "应用内购买": "In-App Purchases",
        "包含 Source SDK": "Includes Source SDK",
        "包含关卡编辑器": "Includes level editor",
        "局域网合作": "LAN Co-op",
        "局域网 PvP": "LAN PvP",
        "大型多人在线游戏": "MMO",
        "多人游戏": "Multi-player",
        "在线合作": "Online Co-op",
        "在线 PvP": "Online PvP",
        "部分支持手柄": "Partial Controller Support",
        "PvP": "PvP",
        "远程同乐": "Remote Play Together",
        "手机远程游戏": "Remote Play on Phone",
        "电视远程游戏": "Remote Play on TV",
        "平板电脑远程游戏": "Remote Play on Tablet",
        "共享/分屏": "Shared/Split Screen",
        "共享/分屏合作": "Shared/Split Screen Co-op",
        "共享/分屏 PvP": "Shared/Split Screen PvP",
        "单人游戏": "Single-player",
        "统计数据": "Stats",
        "Steam 成就": "Steam Achievements",
        "Steam 云": "Steam Cloud",
        "Steam 排行榜": "Steam Leaderboards",
        "Steam 时间线": "Steam Timeline",
        "Steam 集换式卡牌": "Steam Trading Cards",
        "Steam 创意工坊": "Steam Workshop",
        "SteamVR 收藏品": "SteamVR Collectibles",
        "支持追踪手柄": "Tracked Controller Support",
        "仅限 VR": "VR Only",
        "支持 VR": "VR Supported"
    },
    "genre": {
        "动作": "Action",
        "冒险": "Adventure",
        "动画与建模": "Animation & Modeling",
        "音频制作": "Audio Production",
        "休闲": "Casual",
        "设计与插画": "Design & Illustration",
        "抢先体验": "Early Access",
        "免费游戏": "Free To Play",
        "游戏开发": "Game Development",
        "独立游戏": "Indie",
        "大型多人在线游戏": "Massively Multiplayer",
        "照片编辑": "Photo Editing",
        "角色扮演": "RPG",
        "竞速": "Racing",
        "模拟": "Simulation",
        "体育": "Sports",
        "策略": "Strategy",
        "实用工具": "Utilities",
        "视频制作": "Video Production",
        "暴力": "Violent",
        "网络出版": "Web Publishing"
    },
    "price": {
        "免费": "free",
        "0 - 50 元": "low",
        "50 - 100 元": "medium",
        "100 - 150 元": "medium",
        "150 - 200 元": "high",
        "200+ 元": "high"
    },  # 添加空字典，避免 KeyError
    "platform": {
        "Linux": "platforms_linux",
        "Windows": "platforms_windows",
        "Mac": "platforms_mac"
    }  # 同上

}


@app.route('/submit-preferences', methods=['POST'])
def submit_preferences():
    data = request.get_json()
    user_id = session.get('user_id')  # 获取当前登录用户的ID

    if not user_id:
        return jsonify({'status': 'error', 'message': '用户未登录'}), 400

    # 将偏好转换为英文
    def convert_preferences(preferences, type):
        return [translations[type].get(preference, preference) for preference in preferences]

    try:
        # 先删除该用户原有偏好
        with Database.cursor() as cursor:
            cursor.execute("DELETE FROM preferences WHERE user_id = %s", (user_id,))

        # 再处理并插入新偏好
        for preference_type, preferences in data.items():
            english_preferences = convert_preferences(preferences, preference_type)

            for preference in english_preferences:
                query = """
                        INSERT INTO preferences (user_id, prefer, value)
                        VALUES (%s, %s, %s) \
                        """
                form_data = (user_id, preference_type, preference)

                with Database.cursor() as cursor:
                    cursor.execute(query, form_data)

        return jsonify({'status': 'success', 'message': '偏好设置已保存！'})

    except Exception as e:
        print(f"偏好提交失败: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


def generate_wordcloud(text_weights, color, mask_png_path=None):
    # 读取PNG蒙版
    mask = None
    if mask_png_path and Path(mask_png_path).exists():
        try:
            mask = np.array(Image.open(mask_png_path))
            # 使用alpha通道作为蒙版
            if mask.ndim == 3:
                # 反转alpha通道：0变255，255变0
                mask = 255 - mask[:, :, 3]  # 反转alpha通道
        except Exception as e:
            print(f"加载蒙版失败: {e}")

    wc = WordCloud(
        width=600,
        height=400,
        background_color='white',
        font_path='simhei.ttf',
        color_func=lambda *args, **kwargs: color,
        prefer_horizontal=1,
        scale=2,
        mask=mask,  # 使用反转后的蒙版
        contour_width=0,
        contour_color=None,
        collocations=False
    )

    if text_weights:
        wc.generate_from_frequencies(text_weights)
    else:
        # 如果没有数据，生成空图片
        wc.generate_from_text(" ")

    # 转换为base64编码的图片
    img_buffer = io.BytesIO()
    wc.to_image().save(img_buffer, format='PNG')
    img_str = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    return img_str


# 分析评论并生成词云
def analyze_comments(appid):
    with Database.cursor() as cursor:  # 使用 with

        # 查询好评评论
        cursor.execute("""
                       SELECT comments, duration
                       FROM recommendation
                       WHERE appid = %s
                         AND positive = TRUE
                       """, (appid,))
        positive_comments = cursor.fetchall()

        # 查询差评评论
        cursor.execute("""
                       SELECT comments, duration
                       FROM recommendation
                       WHERE appid = %s
                         AND positive = FALSE
                       """, (appid,))
        negative_comments = cursor.fetchall()

        cursor.close()

    # 处理好评数据
    positive_text = ' '.join([comment[0] for comment in positive_comments])
    positive_weights = {}
    if positive_comments:
        # 使用TF-IDF提取关键词，结合游玩时长作为权重
        for comment, duration in positive_comments:
            words = jieba.analyse.extract_tags(
                comment,
                topK=20,
                withWeight=True,
                allowPOS=('n', 'vn', 'v')
            )
            for word, weight in words:
                # 权重 = TF-IDF权重 * 游玩时长系数 (1 + duration/100)
                duration_factor = 1 + (duration / 100) if duration else 1
                combined_weight = weight * duration_factor
                if word in positive_weights:
                    positive_weights[word] += combined_weight
                else:
                    positive_weights[word] = combined_weight

    # 处理差评数据
    negative_text = ' '.join([comment[0] for comment in negative_comments])
    negative_weights = {}
    if negative_comments:
        for comment, duration in negative_comments:
            words = jieba.analyse.extract_tags(
                comment,
                topK=20,
                withWeight=True,
                allowPOS=('n', 'vn', 'v')
            )
            for word, weight in words:
                duration_factor = 1 + (duration / 100) if duration else 1
                combined_weight = weight * duration_factor
                if word in negative_weights:
                    negative_weights[word] += combined_weight
                else:
                    negative_weights[word] = combined_weight

            # 生成词云 - 使用PNG蒙版
            positive_img = generate_wordcloud(
                positive_weights,
                '#62b7e9',
                'static/image/masks/thumbs-up.png'  # 修改为PNG路径
            )

            negative_img = generate_wordcloud(
                negative_weights,
                '#cd5d60',
                'static/image/masks/thumbs-down.png'  # 修改为PNG路径
            )

            return {
                'positive': positive_img,
                'negative': negative_img
            }


@app.route('/wordcloud')
def wordcloud():
    user_name = session.get('user_name')
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录，无法使用'}), 403
    jieba.initialize()
    return render_template("wordcloud.html", user_name=user_name, user_id=user_id)


@app.route('/wordcloud_analyse', methods=['POST'])
def wordcloud_analyse():
    appid = request.form.get('appid')
    if not appid or not appid.isdigit():
        return jsonify({'error': '请输入有效的游戏ID'}), 400
    try:
        result = analyze_comments(int(appid))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(port=8000, debug=True)
