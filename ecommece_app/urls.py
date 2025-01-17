
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

from django.urls import path


urlpatterns = [
    path('', views.home, name="home"),
    path('add_to_cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name="checkout"),
    path('login/', views.login_view, name="login"),
    path('register/', views.register, name="register"),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('orders/', views.order_view, name='order_view'),
    path('category/', views.category, name='category'),
    path('supplier/', views.supplier, name='supplier'),
    path('search/', views.search, name='search'),
    path('products/', views.product_detail, name='products'),
    path('update_cart/', views.update_cart, name='update_cart'),
    path('supplier_login/', views.supplier_login, name='supplier_login'),
    path('dashboard/', views.supplier_dashboard, name='supplier_dashboard'),
    path('add-product/', views.add_product, name='add_product'),
    path('edit_product/', views.edit_product, name='edit_product'), 
    path('delete_product/', views.delete_product, name='delete_product'),
    path('qr_payment/', views.qr_payment, name='qr_payment'),
    
    
   
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
