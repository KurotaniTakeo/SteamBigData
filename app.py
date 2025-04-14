from flask import Flask, render_template, request, redirect, url_for, session, flash
from decouple import config
from pymysql import Connection
from pymysql.cursors import DictCursor
import tomlkit
from contextlib import contextmanager

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
            flash('登录成功！', 'success')
            return render_template('login.html', user_name=user[3], delay_redirect=True)

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
            request.form['preference_category'],
            request.form['preference_price'],
            request.form['age'],
            request.form['gender'],
            request.form['languages'],
            request.form['platforms']
        )

        query = """
        INSERT INTO users 
        (mail, password, user_name, preference_category, preference_price, age, gender, languages, platforms)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
    return render_template("user.html", user_name=user_name)


@app.route('/preference')
def preference():
    user_name = session.get('user_name')
    return render_template("preference.html", user_name=user_name)


if __name__ == '__main__':
    app.run(port=8000, debug=True)