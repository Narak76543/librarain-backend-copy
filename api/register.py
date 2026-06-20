# ========== register auth user ====================
from .auth_user.views import *
#========== register user profile ==================
from .user_profile.views import *
# ======= register categories module ===============
from .categories.views import *
# ====== register books module =====================
from .books.views import *
# ===== register cart module =======================
from .cart.views import *
# ====== register order module ====================
from .orders.views import *
# =========== register whishlist =================
from .wishlist.views import *
# =========== register reports ===================
from .reports.views import *
from .telegram_bots.bot_polling import *