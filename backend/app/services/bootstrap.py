from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import Permission, Role, User

ROLE_DEFINITIONS = {
    "admin": ["documents:read", "documents:write", "admin:read", "users:read"],
    "knowledge_maintainer": ["documents:read", "documents:write"],
    "business_user": ["documents:read"],
    "readonly_user": ["documents:read"],
}

PERMISSION_DESCRIPTIONS = {
    "documents:read": "查看资料",
    "documents:write": "上传和维护资料",
    "admin:read": "查看管理后台",
    "users:read": "查看用户信息",
}

ROLE_DESCRIPTIONS = {
    "admin": "管理员",
    "knowledge_maintainer": "知识维护人员",
    "business_user": "业务用户",
    "readonly_user": "只读用户",
}


def seed_defaults(db: Session) -> None:
    permissions: dict[str, Permission] = {}
    for name, description in PERMISSION_DESCRIPTIONS.items():
        permission = db.query(Permission).filter(Permission.name == name).one_or_none()
        if permission is None:
            permission = Permission(name=name, description=description)
            db.add(permission)
        permissions[name] = permission

    for role_name, permission_names in ROLE_DEFINITIONS.items():
        role = db.query(Role).filter(Role.name == role_name).one_or_none()
        if role is None:
            role = Role(name=role_name, description=ROLE_DESCRIPTIONS[role_name])
            db.add(role)
        role.permissions = [permissions[name] for name in permission_names]

    db.flush()
    admin = db.query(User).filter(User.username == settings.default_admin_username).one_or_none()
    admin_role = db.query(Role).filter(Role.name == "admin").one()
    if admin is None:
        admin = User(
            username=settings.default_admin_username,
            password_hash=hash_password(settings.default_admin_password),
            display_name="系统管理员",
            roles=[admin_role],
        )
        db.add(admin)
    elif admin_role not in admin.roles:
        admin.roles.append(admin_role)

    db.commit()
