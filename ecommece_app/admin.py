from django.contrib import admin
from .models import *
from .forms import *

admin.site.register(Customer, CustomerAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(StockInvoice, StockInvoiceAdmin)
admin.site.register(Supplier, SupplierAdmin)
admin.site.register(Category)



