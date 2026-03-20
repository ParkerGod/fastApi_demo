from sqlalchemy.orm import Session
from .. import models
import bcrypt
from ..schemas import schemas_user

# 数据交互

SECRET_KEY = "wangcheng"


# 获取密码哈希值
def get_password_hash(password):
    # 使用 bcrypt 直接处理，确保编码正确
    password_bytes = password.encode('utf-8')[:72]  # bcrypt 限制 72 字节
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password, hashed_password):
    # 使用 bcrypt 直接验证
    plain_bytes = plain_password.encode('utf-8')[:72]
    hash_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hash_bytes)


# 根据用户ID获取用户信息
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


# 根据 email 获取用户信息
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


# 根据用户邮箱和密码获取用户信息
def get_user_by_login(db: Session, email: str, password: str):
    fake_hashed_password = password + SECRET_KEY
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return False
    if not verify_password(fake_hashed_password, user.hashed_password):
        return False
    return user


# 获取所有用户信息
def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


# 创建用户
def create_user(db: Session, user: schemas_user.UserCreate):
    fake_hashed_password = get_password_hash(user.password + SECRET_KEY)
    username = user.email.split('@')[0] if '@' in user.email else user.email
    db_user = models.User(email=user.email, hashed_password=fake_hashed_password, username=username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
