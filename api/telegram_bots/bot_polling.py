import asyncio
import httpx
import logging
from core.db import Session
from api.auth_user.models import TBL_AUTH_USER
from core.db import engine
from config import configs

logger = logging.getLogger(__name__)

BOT_TOKEN = configs.TELEGRAM_BOT_TOKEN
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

async def process_update(update: dict):
    try:
        message = update.get("message")
        if not message:
            return

        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        from_user = message.get("from", {})
        telegram_username = from_user.get("username")
        
        if not chat_id or not text.startswith("/start"):
            return

        parts = text.split(" ")
        if len(parts) == 2:
            # Example: /start login_123e4567-e89b-12d3-a456-426614174000
            # OR       /start 123e4567-e89b-12d3-a456-426614174000 (linking)
            start_payload = parts[1].strip()
            
            with Session() as db:
                if start_payload.startswith("login_"):
                    # This is a deep link for LOGIN/REGISTER
                    login_token = start_payload.replace("login_", "")
                    
                    # Look for existing user by chat_id
                    user = db.query(TBL_AUTH_USER).filter(TBL_AUTH_USER.telegram_chat_id == str(chat_id)).first()
                    
                    if not user:
                        # Auto-register new user
                        import secrets
                        from api.auth_user.security import hash_password
                        
                        dummy_email = f"telegram_{chat_id}@telegram.auth"
                        full_name = from_user.get("first_name", "Telegram User")
                        if from_user.get("last_name"):
                            full_name += f" {from_user.get('last_name')}"
                            
                        user = TBL_AUTH_USER(
                            full_name=full_name,
                            email=dummy_email,
                            password_hash=hash_password(secrets.token_urlsafe(32)),
                            telegram_chat_id=str(chat_id),
                            is_active=True,
                            is_verified=True,
                        )
                        db.add(user)
                        db.flush()
                        
                        from api.user_profile.models import TBL_USER_PROFILE
                        new_profile = TBL_USER_PROFILE(user_id=user.id, telegram=telegram_username)
                        db.add(new_profile)
                        db.flush()
                        
                        from api.auth_user.models import TBL_AUTH_ROLE, TBL_AUTH_USER_ROLE
                        default_role = db.query(TBL_AUTH_ROLE).filter(TBL_AUTH_ROLE.role_code == "USER").first()
                        if default_role:
                            db.add(TBL_AUTH_USER_ROLE(user_id=user.id, role_id=default_role.id))
                        db.commit()
                        db.refresh(user)
                    
                    # Now update the token
                    from api.auth_user.models import TBL_TELEGRAM_LOGIN_TOKEN
                    token_entry = TBL_TELEGRAM_LOGIN_TOKEN(
                        token=login_token,
                        user_id=user.id,
                        is_authenticated=True
                    )
                    db.merge(token_entry)
                    db.commit()
                    
                    await send_telegram_message(
                        chat_id, 
                        f"✅ Logged in successfully as {user.full_name}! Please use your phone's recent apps to switch back to the Librarain app."
                    )
                    
                else:
                    # Linking existing account
                    user_id = start_payload
                    user = db.query(TBL_AUTH_USER).filter(TBL_AUTH_USER.id == user_id).first()
                    if user:
                        user.telegram_chat_id = str(chat_id)
                        
                        if not user.profile:
                            from api.user_profile.models import TBL_USER_PROFILE
                            new_profile = TBL_USER_PROFILE(user_id=user.id)
                            db.add(new_profile)
                            db.commit()
                            db.refresh(user)
                            
                        if user.profile and telegram_username:
                            user.profile.telegram = telegram_username
                            
                        db.commit()
                        
                        success_msg = f"🎉 Welcome {user.full_name}! Your Telegram account has been successfully linked to your Librarain profile. You will now receive order updates here!"
                        await send_telegram_message(chat_id, success_msg)
                    else:
                        await send_telegram_message(chat_id, "❌ Sorry, we could not find a user with that ID.")
        else:
            await send_telegram_message(chat_id, "Welcome to Librarain! To link your account, please click the 'Link Telegram' button in the mobile app.")
    
    except Exception as e:
        logger.error(f"Error processing telegram update: {e}")

async def start_telegram_polling():
    last_update_id = 0
    timeout = 30
    
    logger.info("Starting Telegram Bot Polling...")
    
    async with httpx.AsyncClient(timeout=timeout + 5) as client:
        while True:
            try:
                response = await client.get(
                    f"{TELEGRAM_API_URL}/getUpdates",
                    params={"offset": last_update_id, "timeout": timeout},
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        updates = data.get("result", [])
                        for update in updates:
                            await process_update(update)
                            update_id = update.get("update_id")
                            if update_id and update_id >= last_update_id:
                                last_update_id = update_id + 1
            except Exception as e:
                logger.error(f"Telegram polling error: {e}")
                await asyncio.sleep(5)

async def send_telegram_message(chat_id: str, text: str, reply_markup: dict = None):
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json=payload,
            )
            if response.status_code != 200:
                logger.error(f"Telegram API Error: {response.text}")
    except Exception as e:
        logger.error(f"Failed to send telegram message: {e}")

def send_telegram_message_sync(chat_id: str, text: str, reply_markup: dict = None):
    import requests
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
            
        requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json=payload,
        )
    except Exception as e:
        logger.error(f"Failed to send telegram message (sync): {e}")
