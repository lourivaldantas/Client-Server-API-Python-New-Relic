from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    username: str
    email: str


class UserRead(UserCreate):
    id: int
