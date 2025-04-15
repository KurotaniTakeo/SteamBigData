from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from decouple import config
from pymysql import Connection
from pymysql.cursors import DictCursor
import tomlkit
from contextlib import contextmanager
import ast
import re



app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = config('SECRET_KEY')

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
        """获取数据库连接（自动关闭）"""
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
        """获取数据库游标（自动提交/回滚并关闭）"""
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
        VALUES (%s, %s, %s, %s, %s)
        """

        try:
            with Database.cursor() as cursor:
                cursor.execute(query, form_data)
            flash('注册成功！', 'success')
        except Exception as e:
            flash(f'注册失败：{str(e)}', 'danger')

        return redirect(url_for('register'))

    return render_template("register.html")


@app.route('/user')
def user():
    user_name = session.get('user_name')
    user_id = session.get('user_id')
    return render_template("user.html", user_name=user_name, user_id=user_id)


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
from flask import request  # 确保你有导入这个

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
            page_numbers = [1, '...', total_pages - 5, total_pages - 4, total_pages - 3, total_pages - 2, total_pages - 1, total_pages]
        else:
            page_numbers = [1, '...', page - 1, page, page + 1, '...', total_pages]

    return render_template("SRS.html",
                           games=datalist,
                           page=page,
                           total_pages=total_pages,
                           page_numbers=page_numbers,
                           user_name=user_name,
                           user_id=user_id)

from recommendations import generate_recommendations
# 刷新偏好
@app.route('/refresh_recommendations', methods=['POST'])
def refresh_recommendations():
    try:
        generate_recommendations(refresh=True)
        return jsonify({"status": "success", "message": "推荐列表已刷新!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/price_distribution')
def price_distribution():
    user_name = session.get('user_name')
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': '未登录，无法使用SRS'}), 403
    return render_template("steam_price_distribution.html", user_name=user_name, user_id=user_id)


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
                    VALUES (%s, %s, %s)
                """
                form_data = (user_id, preference_type, preference)

                with Database.cursor() as cursor:
                    cursor.execute(query, form_data)

        return jsonify({'status': 'success', 'message': '偏好设置已保存！'})

    except Exception as e:
        print(f"偏好提交失败: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(port=8000, debug=True)