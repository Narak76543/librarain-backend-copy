# ================= user profile api ===========================
from fastapi import Depends, File, UploadFile, Request
from fastapi.encoders import jsonable_encoder
from starlette import status
from api.auth_user.models import TBL_AUTH_USER
from api.auth_user.security import get_current_user
from api.auth_user.views import response, serialize_user
from api.user_profile.models import TBL_USER_PROFILE
from core.db import get_db
from main import app
from sqlalchemy.orm import Session
from config import configs
from .schemas import *
import logging
from core.logger import write_log, LogAction, LogModule

logger = logging.getLogger(__name__)

from api.auth_user import schemas as auth_schemas
from api.user_profile import schemas as profile_schemas


@app.get("/api/v1/users/me", tags=["User Profile"])
def get_my_profile(
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    profile = (
        db.query(TBL_USER_PROFILE)
        .filter(TBL_USER_PROFILE.user_id == current_user.id)
        .first()
    )

    if not profile:
        profile = TBL_USER_PROFILE(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    user_data    = serialize_user(current_user)
    profile_data = jsonable_encoder(
        profile_schemas.UserProfileResponse.model_validate(profile)
    )

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Profile retrieved successfully",
        data={
            "user"   : user_data,
            "profile": profile_data,
        },
    )


@app.put("/api/v1/users/me", tags=["User Profile"])
def update_my_profile(
    request     : Request,
    payload     : profile_schemas.UserProfileUpdate,
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    profile = (
        db.query(TBL_USER_PROFILE)
        .filter(TBL_USER_PROFILE.user_id == current_user.id)
        .first()
    )

    if not profile:
        profile = TBL_USER_PROFILE(user_id=current_user.id)
        db.add(profile)

    update_data = payload.model_dump(exclude_unset=True)
    old_values = {}
    for field, value in update_data.items():
        old_values[field] = str(getattr(profile, field))
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    if update_data:
        write_log(
            db          = db,
            action      = LogAction.PROFILE_UPDATED,
            module      = LogModule.PROFILE,
            description = f"User profile updated",
            user_id     = current_user.id,
            user_email  = current_user.email,
            user_role   = "USER",
            entity_type = "user_profile",
            entity_id   = str(current_user.id),
            old_value   = old_values,
            new_value   = {k: str(v) for k, v in update_data.items()},
            request     = request,
            commit      = True,
        )

    profile_data = jsonable_encoder(
        profile_schemas.UserProfileResponse.model_validate(profile)
    )

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Profile updated successfully",
        data={
            "profile": profile_data,
        },
    )

@app.post("/api/v1/users/me/avatar", tags=["User Profile"])
async def upload_avatar(
    request     : Request,
    file        : UploadFile    = File(...),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    allowed_types = {"image/jpeg", "image/png", "image/webp"}

    if file.content_type not in allowed_types:
        return response(
            ok          = False,
            status_code = status.HTTP_400_BAD_REQUEST,
            message     = "Only JPEG, PNG and WebP images are allowed",
        )

    try:
        import cloudinary
        import cloudinary.uploader

        if not all(
            [
                configs.CLOUDINARY_CLOUD_NAME,
                configs.CLOUDINARY_API_KEY,
                configs.CLOUDINARY_API_SECRET,
            ]
        ):
            return response(
                ok          = False,
                status_code = status.HTTP_502_BAD_GATEWAY,
                message     = "Cloudinary configuration is missing.",
            )

        cloudinary.config(
            cloud_name = configs.CLOUDINARY_CLOUD_NAME,
            api_key    = configs.CLOUDINARY_API_KEY,
            api_secret = configs.CLOUDINARY_API_SECRET,
            secure     = True,
        )

        contents = await file.read()
        result   = cloudinary.uploader.upload(
            contents,
            folder          = f"avatars/{current_user.id}",
            resource_type   = "image",
            transformation  = [{"width": 400, "height": 400, "crop": "fill"}],
        )
        avatar_url = result["secure_url"]

    except Exception:
        logger.exception("Failed to upload avatar to Cloudinary")
        return response(
            ok          = False,
            status_code = status.HTTP_502_BAD_GATEWAY,
            message     = "Failed to upload avatar. Check Cloudinary configuration.",
        )

    profile = (
        db.query(TBL_USER_PROFILE)
        .filter(TBL_USER_PROFILE.user_id == current_user.id)
        .first()
    )

    if not profile:
        profile = TBL_USER_PROFILE(user_id=current_user.id)
        db.add(profile)

    profile.avatar_url = avatar_url
    db.commit()
    db.refresh(profile)

    write_log(
        db          = db,
        action      = LogAction.AVATAR_UPLOADED,
        module      = LogModule.PROFILE,
        description = f"User avatar updated",
        user_id     = current_user.id,
        user_email  = current_user.email,
        user_role   = "USER",
        entity_type = "user_profile",
        entity_id   = str(current_user.id),
        new_value   = {"avatar_url": avatar_url},
        request     = request,
        commit      = True,
    )

    profile_data = jsonable_encoder(
        profile_schemas.UserProfileResponse.model_validate(profile)
    )

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Avatar uploaded successfully",
        data={
            "profile": profile_data,
        },
    )

# =============== save fcm token =============================
@app.post("/api/v1/users/me/fcm-token", tags=["User Profile"])
def save_fcm_token(
    payload     : FCMTokenRequest,
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    profile = (
        db.query(TBL_USER_PROFILE)
        .filter(TBL_USER_PROFILE.user_id == current_user.id)
        .first()
    )
    if not profile:
        profile = TBL_USER_PROFILE(user_id=current_user.id)
        db.add(profile)

    profile.fcm_token = payload.fcm_token
    db.commit()

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "FCM token saved",
    )