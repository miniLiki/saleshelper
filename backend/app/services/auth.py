from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRead

security = HTTPBearer(auto_error=False)


def user_to_read(user: User) -> UserRead:
    roles = sorted(role.name for role in user.roles)
    permissions = sorted({permission.name for role in user.roles for permission in role.permissions})
    return UserRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=roles,
        permissions=permissions,
    )


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username).one_or_none()
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AppError(401, "未登录或登录已过期")
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise AppError(401, "无效的访问令牌") from exc
    user_id = payload.get("sub")
    if user_id is None:
        raise AppError(401, "无效的访问令牌")
    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise AppError(401, "用户不存在或已停用")
    return user


def require_permission(permission_name: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        permissions = {permission.name for role in current_user.roles for permission in role.permissions}
        if permission_name not in permissions:
            raise AppError(403, "没有权限执行此操作")
        return current_user

    return dependency
