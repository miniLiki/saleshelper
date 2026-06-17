from pydantic import BaseModel


class UserRead(BaseModel):
    id: int
    username: str
    display_name: str
    is_active: bool
    roles: list[str]
    permissions: list[str]
