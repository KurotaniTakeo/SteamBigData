from flask import Flask, render_template, request, redirect, url_for, session, flash
from decouple import config
from pymysql import Connection

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = config('SECRET_KEY')
@app.route('/')
def index():
    user_name = session.get('user_name')  # 从 session 读取
    return render_template('index.html', user_name=user_name)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # 获取表单数据
        mail = request.form['mail']
        password = request.form['password']

        # 查询数据库
        con = Connection(
            host='localhost',
            port=3306,
            user='root',
            password='123456',
            database='steam_games'
        )
        cursor = con.cursor()
        query = "SELECT * FROM users WHERE mail = %s AND password = %s"
        cursor.execute(query, (mail, password))
        user = cursor.fetchone()
        cursor.close()
        con.close()

        if user:
            user_name = user[3]
            session['user_name'] = user_name  # 保存到 session
            flash('登录成功！', 'success')
            return render_template('login.html', user_name=user_name, delay_redirect=True)
        else:
            flash('邮箱或密码错误！', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    # 清除session中的username值
    session.pop('user_name', None)
    # 重定向到登录页面或其他页面
    return redirect(url_for('index'))




@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 获取表单数据
        mail = request.form['mail']
        password = request.form['password']
        user_name = request.form['user_name']
        preference_category = request.form['preference_category']
        preference_price = request.form['preference_price']
        age = request.form['age']
        gender = request.form['gender']
        languages = request.form['languages']
        platforms = request.form['platforms']

        # 插入数据到数据库
        con = Connection(
            host='localhost',
            port=3306,
            user='root',
            password='123456',
            database='steam_games'
        )
        cursor = con.cursor()
        query = """
        INSERT INTO users (mail, password, user_name, preference_category, preference_price, age, gender, languages, platforms)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            cursor.execute(query, (mail, password, user_name, preference_category, preference_price, age, gender, languages, platforms))
            con.commit()
            flash('注册成功！', 'success')  # 设置成功消息
        except Exception as e:
            con.rollback()
            flash(f'注册失败：{str(e)}', 'danger')  # 设置错误消息
        finally:
            cursor.close()
            con.close()

        return redirect(url_for('register'))  # 重定向到注册页面

    return render_template("register.html")

@app.route('/user')
def user():
    user_name = session.get('user_name')  # 从 session 读取
    return render_template("user.html",user_name=user_name)

@app.route('/preference')
def preference():
    user_name = session.get('user_name')  # 从 session 读取
    return render_template("preference.html",user_name=user_name)




if __name__ =='__main__':
    app.run(port=8000,debug=True)