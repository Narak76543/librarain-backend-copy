import requests
import logging
import google.auth.transport.requests
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

SERVICE_ACCOUNT_FILE = "firebase-service-account.json"
PROJECT_ID = "librarain"
FCM_URL = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"

def get_access_token() -> str:
    import os
    import json
    firebase_json_str = os.getenv("FIREBASE_JSON")
    
    if firebase_json_str:
        # Load from Railway Environment Variable
        creds_dict = json.loads(firebase_json_str)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"],
        )
    else:
        # Load from Local File
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"],
        )
        
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    return credentials.token

def send_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: dict = {},
) -> bool:
    try:
        payload = {
            "message": {
                "token": fcm_token,
                "notification": {"title": title, "body": body},
                "data": {k: str(v) for k, v in data.items()},
                "android": {
                    "notification": {
                        "sound": "default",
                        "click_action": "FLUTTER_NOTIFICATION_CLICK",
                    }
                },
            }
        }

        res = requests.post(
            FCM_URL,
            headers={
                "Authorization": f"Bearer {get_access_token()}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

        if res.status_code == 200:
            logger.info(f"====== notification sent: {title} ========")
            return True
        else :
            logger.error(f"====== FCM error {res.status_code}: {res.text}")
            return False

    except Exception as e :
        logger.exception(f"======= FCM faild : {e}")
        return False

# ======= get fcm token =========
def get_user_fcm_token (db , user_id ) ->  str | None :
    from api.user_profile.models import TBL_USER_PROFILE

    profile = (
        db.query (TBL_USER_PROFILE)
        .filter(TBL_USER_PROFILE.user_id == user_id)
        .first()
    )
    return profile.fcm_token if profile and profile.fcm_token else None 

# ==== Notification functions ==========
def notify_order_placed(db , user_id , order_id : str , total : str):
    token = get_user_fcm_token(db , user_id )

    if not token :
        return
    
    send_notification (
        
        fcm_token = token,
        title     = "Order Placed",
        body      = f"Order #{order_id[:8].upper()} of ${total} confirmed",
        data      = {"type" : "order_confirmed" ,"order_id" : order_id},
    )
# ====== notify order status ===========
def notify_order_status(db, user_id, order_id: str, new_status: str):
    token = get_user_fcm_token(db, user_id)
    if not token:
        return
    messages = {
        "processing": ("========Order Processing =========== ",
                       f"Order #{order_id[:8].upper()} is being processed!"),
        "delivered" : ("======== Order Delivered! ===============",
                       f"Order #{order_id[:8].upper()} delivered. Enjoy! "),
        "cancelled" : ("======== Order Cancelled ====================",
                       f"Order #{order_id[:8].upper()} was cancelled."),
    }
    if new_status not in messages:
        return
    title, body = messages[new_status]
    send_notification(
        fcm_token = token,
        title     = title,
        body      = body,
        data      = {
            "type"    : "order_status",
            "order_id": order_id,
            "status"  : new_status,
        },
    )


def notify_password_reset(db, user_id):
    token = get_user_fcm_token(db, user_id)
    if not token:
        return
    send_notification(
        fcm_token = token,
        title     = "======= Password Reset Successful ==========",
        body      = "Your password was changed. If this wasn't you contact support.",
        data      = {"type": "password_reset"},
    )