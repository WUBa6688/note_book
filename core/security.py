import hashlib


def hash_password(password: str) -> str:
    """SHA-256 哈希密码。"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    """验证密码是否匹配。"""
    return hash_password(password) == stored_hash


def is_valid_password_format(password: str) -> bool:
    """检查密码格式：4位或6位纯数字。"""
    return password.isdigit() and len(password) in (4, 6)
