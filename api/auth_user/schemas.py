from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

try:
    from pydantic import ConfigDict, field_validator
except ImportError:
    ConfigDict = None
    from pydantic import validator as field_validator

def validate_bcrypt_password_length(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password cannot be longer than 72 bytes")
    return value

class RegisterRequest(BaseModel):
    full_name: str = Field(..., max_length=150)
    email    : EmailStr
    phone    : Optional[str] = Field(default=None, max_length=30)
    password : str = Field(..., min_length=6)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_bcrypt_password_length(value)

class LoginRequest(BaseModel):

    email   : EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    if ConfigDict:
        model_config = ConfigDict(populate_by_name=True)

    refresh_token: str = Field(..., alias="refreshToken")

    if not ConfigDict:
        class Config:
            allow_population_by_field_name = True

class LogoutRequest(BaseModel):
    if ConfigDict:
        model_config = ConfigDict(populate_by_name=True)

    refresh_token: str = Field(..., alias="refreshToken")

    if not ConfigDict:
        class Config:
            allow_population_by_field_name = True

class UserResponse(BaseModel):
    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)

    id         : UUID
    full_name  : str
    email      : str
    phone      : Optional[str] = None
    is_active  : bool
    is_verified: bool

    if not ConfigDict:
        class Config:
            orm_mode = True

class ApiResponse(BaseModel):
    ok     : bool
    status : int
    message: str
    data   : Optional[Any] = None

class ResetAttemptRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    channel: Optional[str] = "email"


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp_code: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str = Field(..., min_length=6)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_bcrypt_password_length(value)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)

    @field_validator("current_password")
    @classmethod
    def validate_current_password(cls, value: str) -> str:
        return validate_bcrypt_password_length(value)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_bcrypt_password_length(value)

class GoogleLoginRequest(BaseModel):
    id_token   : str
    device_id  : Optional[str] = None
    device_name: Optional[str] = None

# New : Two-Step registration + Telegram OTP Schemas

class RequestRegistrationEmail(BaseModel) :
    email : EmailStr

class RequestPhoneOtp(BaseModel):
    phone : str = Field(..., min_length=8 , max_length=20)

class VerifyPhoneOtp(BaseModel):
    phone    : str = Field(..., min_length=8 ,max_digits=20 )
    otp_code : str = Field(..., min_length=6 , max_length=6)

class ResgisterRequest(BaseModel):
    full_name             : str = Field(..., max_length=150)
    email                 : EmailStr
    phone                 : Optional[str] = Field(default=None, max_length=30)
    password              : str = Field(..., min_length=6)
    registration_reference: str
    phone_reference       : Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_bcrypt_password_length(value)

