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
from api.system_log.models import TBL_SYSTEM_LOG
from .wishlist.views import *
# =========== register invoices =================
from .invoices.views import *
# =========== register reports ===================
from .reports.views import *
from .telegram_bots.bot_polling import *

from main import app
from api.suppliers.views import router as supplier_router
app.include_router(supplier_router)
from api.purchase_orders.views import router as po_router
app.include_router(po_router)
from api.inventory.views import router as inventory_router
app.include_router(inventory_router)
from api.system_log.views import router as system_log_router
app.include_router(system_log_router)