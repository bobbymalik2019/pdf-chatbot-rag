from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)

class NewUser(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    display_name: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=12, max_length=1024)
    roles: list[str] = Field(default_factory=lambda: ['USER'])

class RoleChange(BaseModel):
    roles: list[str] = Field(min_length=1)
