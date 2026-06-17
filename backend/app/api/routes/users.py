from fastapi import APIRouter, Depends

from app.models.user import User
from app.schemas.user import UserRead
from app.services.auth import get_current_user, user_to_read

router = APIRouter()


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return user_to_read(current_user)
