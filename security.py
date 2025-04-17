import bcrypt


def hash_password(password: str) -> str:
    """哈希密码"""
    print(f"原始密码: {password}")  # 调试输出
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    hashed_str = hashed.decode('utf-8')
    print(f"生成的哈希: {hashed_str}")  # 调试输出
    return hashed_str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    print(f"验证输入: 明文='{plain_password}', 哈希='{hashed_password}'")  # 调试输出
    try:
        result = bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
        print(f"验证结果: {'成功' if result else '失败'}")  # 调试输出
        return result
    except Exception as e:
        print(f"验证异常: {str(e)}")  # 调试输出
        return False

