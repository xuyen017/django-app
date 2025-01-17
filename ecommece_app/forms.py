from django import forms
from .models import *
from django.contrib import admin
from django.utils.html import format_html
from django.db import transaction
from datetime import datetime
from django.db.models import Sum, F
from django.shortcuts import render
from .models import Product, OrderDetail, StockInvoiceDetail

# from django.core.mail import send_mail
# from django.conf import settings

# Inline cho OrderDetail
class OrderDetailInline(admin.TabularInline):  # Hoặc admin.StackedInline nếu bạn muốn hiển thị dạng dọc
    model = OrderDetail
    extra = 1  # Số dòng trống mặc định để thêm sản phẩm mới
    fields = ('product', 'quantity', 'total_price')  # Các trường hiển thị trong inline
    readonly_fields = ('total_price',)

    # Tính tổng tiền cho từng sản phẩm
    def total_price(self, obj):
        if obj.product and obj.quantity:
            return obj.product.price * obj.quantity
        return 0
    total_price.short_description = "Tổng tiền (VND)"

# Admin cho Order
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderDetailInline]  # Thêm OrderDetailInline vào OrderAdmin
    list_display = ('order_id', 'customer', 'order_date', 'status', 'payment_method', 'total_amount', 'shipping_address')  # Hiển thị danh sách đơn hàng
    list_editable = ('status',)
    readonly_fields = ('total_amount',)  # Đặt total_amount là readonly
    

    def save_model(self, request, obj, form, change):
            # Lưu đối tượng Order để đảm bảo có khóa chính
            super().save_model(request, obj, form, change)
    # def save_model(self, request, obj, form, change):
    #     # Kiểm tra nếu trạng thái đơn hàng thay đổi và được xác nhận
    #     if 'status' in form.changed_data and obj.status == 'Đã xác nhận':  # Bạn có thể thay đổi giá trị trạng thái này theo yêu cầu
    #         # Gửi email khi đơn hàng được xác nhận
    #         self.send_confirmation_email(obj)

    #     # Lưu đối tượng Order để đảm bảo có khóa chính
    #     super().save_model(request, obj, form, change)

    # def send_confirmation_email(self, order):
    #     """Gửi email xác nhận đơn hàng"""
    #     subject = f"Đơn hàng #{order.order_id} đã được xác nhận"
    #     message = f"Chào {order.customer.name},\n\nĐơn hàng của bạn đã được xác nhận.\n\nCảm ơn bạn đã mua hàng từ chúng tôi!\n\nThông tin đơn hàng:\nMã đơn hàng: {order.order_id}\nNgày đặt hàng: {order.order_date}\nTrạng thái: {order.status}\n\nTrân trọng,\nCông ty của bạn"
    #     from_email = settings.DEFAULT_FROM_EMAIL
    #     recipient_list = [order.customer.email]  # Gửi email cho khách hàng

    #     # Gửi email
    #     send_mail(subject, message, from_email, recipient_list)

# Inline  cho productimage
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'is_main')  # Các trường hiển thị
    list_display = ('product', 'image', 'is_main')

    # Thêm một action tùy chỉnh
    actions = ['set_main_image']

    @admin.action(description="Set this image as main")
    @transaction.atomic
    def set_main_image(self, request, queryset):
        for image in queryset:
            # Đặt tất cả các ảnh khác của cùng sản phẩm thành False
            ProductImage.objects.filter(product=image.product).update(is_main=False)
            # Đặt ảnh hiện tại là True
            image.is_main = True
            image.save()
        self.message_user(request, "Selected image(s) have been set as main.")

# admin cho Product
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = ('get_product_id', 'get_product_name', 'get_price', 'main_image','get_total_quantity_imported','available_stock')
    
    readonly_fields = ('total_quantity_imported','available_stock')
    list_filter = ('is_main',)  # Thêm bộ lọc để dễ phân biệt
    
    def get_product_id(self, obj):
        return obj.product_id
    get_product_id.short_description = 'id sản phẩm'
    def get_product_name(self, obj):
        return obj.name
    get_product_name.short_description = 'tên sản phẩm'
    def get_price(self, obj):
        return obj.price
    get_price.short_description = 'giá'
    def get_total_quantity_imported(self, obj):
        return obj.total_quantity_imported()
    get_total_quantity_imported.short_description = 'SL'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_staff:  # Chỉ admin có thể thấy tất cả sản phẩm
            return qs
        return qs.filter(is_main=False) 
    def main_image(self, obj):
        main_image = obj.images.filter(is_main=True).first()
        if main_image :
            return format_html(f'<img src="{main_image.image.url}" style="height: 50px; width: 50px; object-fit: cover;" />')
        return "No Main Image"  # Nếu không có ảnh chính
    main_image.short_description = "Ảnh chính"  # Đặt tiêu đề cho cột
    def available_stock(self, obj):
        return obj.available_stock()
    available_stock.short_description = "Số lượng còn lại trong kho"
    
    # Định nghĩa Action: Xem báo cáo mà không cần chọn sản phẩm
    actions = ['view_sales_report']

    def view_sales_report(self, request, queryset):
        """Xem báo cáo sản phẩm bán chạy nhất và lợi nhuận mà không cần chọn sản phẩm"""
        start_date = datetime.now().replace(day=1)
        end_date = datetime.now()

        # Lấy các sản phẩm bán chạy từ OrderDetail
        queryset = (
            OrderDetail.objects
            .filter(order__order_date__range=(start_date, end_date))
            .values('product')
            .annotate(
                total_sold=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('product__price'))
            )
            .order_by('-total_sold')
        )

        # Tạo danh sách dữ liệu sản phẩm
        sales_data = []
        for item in queryset:
            product = Product.objects.get(product_id=item['product'])
            sales_data.append({
                'product': product,
                'total_sold': item['total_sold'],
                'total_revenue': item['total_revenue'],
                'profit': self.calculate_profit(product, item['total_sold'])
            })

        context = {
            'sales_data': sales_data,
            'title': 'Báo cáo Sản phẩm Bán Chạy Nhất'
        }

        # Trả về kết quả dưới dạng HTML
        return render(request, 'admin/sales_report.html', context)

    # Tính lợi nhuận (doanh thu - giá nhập)
    def calculate_profit(self, product, total_sold):
        total_revenue = total_sold * product.price
        stock_details = StockInvoiceDetail.objects.filter(product=product)
        if stock_details.exists():
            avg_cost_price = sum(item.unit_price * item.quantity for item in stock_details) / sum(item.quantity for item in stock_details)
        else:
            avg_cost_price = 0
        total_cost = total_sold * avg_cost_price
        return total_revenue - total_cost if total_revenue else 0

    # Đặt tên cho Action
    view_sales_report.short_description = "Xem Báo Cáo Sản Phẩm Bán Chạy Nhất"
# inline cho StockInvoicedetail
class StockInvoiceDetailInline(admin.TabularInline):
    model= StockInvoiceDetail
    extra = 1
    fields = ('product','quantity', 'unit_price', 'expiration_date','total_quantity')
    readonly_fields = ('total_price','total_quantity')
    def total_quantity(self, obj):
        if obj.product:
            return obj.product.total_quantity_imported()
        return 0
    total_quantity.short_description = "Tổng số lượng đã nhập"

    # Tính tổng tiền cho từng sản phẩm
    def total_price(self, obj):
        if obj.unit_price and obj.quantity:
            return obj.unit_price * obj.quantity
        return 0
    total_price.short_description = "Tổng tiền (VND)"

#admin cho StockInvoi
class StockInvoiceAdmin(admin.ModelAdmin):
    inlines = [StockInvoiceDetailInline]
    list_display = ('invoice_id', 'name', 'invoice_date', 'total_amount')  # Hiển thị tổng tiền
    readonly_fields = ('total_amount',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)  # Lưu hóa đơn

        # Tính toán tổng tiền dựa trên chi tiết hóa đơn nếu có
        if obj.pk:  # Đảm bảo có invoice_id trước khi tính tổng tiền
            obj.total_amount = sum(
                detail.unit_price * detail.quantity
                for detail in obj.stockinvoicedetail_set.all()  # Truy cập các chi tiết hóa đơn liên kết
            )
            obj.save()  # Lưu lại hóa đơn với tổng tiền đã tính

class CustomerAdmin(admin.ModelAdmin):
    model = Customer
    list_display = ('name', 'address')
class SupplierAdmin(admin.ModelAdmin):
    model = Supplier
    list_display = ('name', 'phone', 'address')

#=======================user form==========================

class CustomerRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone', 'address', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        email = cleaned_data.get('email')

        if Customer.objects.filter(email=email).exists():
            raise ValidationError("Tài khoản đã tồn tại vui lòng đăng nhập")
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Mật khẩu nhập không khớp")
        
class CustomLoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="password")

class ProfileForm(forms.Form):
    phone = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    address = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

# list_display	Chọn các cột hiển thị	('id', 'customer', 'status')
# list_display_links	Chọn cột có thể click vào để mở chi tiết	('id', 'customer')
# list_editable	Chỉnh sửa trực tiếp trong danh sách	('status',)
# list_filter	Bộ lọc ở thanh bên phải	('status', 'order_date')
# search_fields	Tìm kiếm theo trường	('customer__name', 'status')
# ordering	Sắp xếp mặc định	('-order_date',)
# list_per_page	Số hàng hiển thị mỗi trang	20

# Model Ảo - Kết hợp dữ liệu từ Product, OrderItem và Category
# class BestSellingProduct:
#     def __init__(self, product, category, total_sold, total_revenue):
#         self.product = product
#         self.category = category
#         self.total_sold = total_sold
#         self.total_revenue = total_revenue

# #Admin Model để hiển thị sản phẩm bán chạy nhất
# class BestSellingProductAdmin(admin.ModelAdmin):
#     list_display = ('product_link', 'category', 'total_sold', 'total_revenue')

#     def get_queryset(self, request):
#         start_date = datetime.now().replace(day=1)
#         end_date = datetime.now()

#         #  Truy vấn số lượng sản phẩm bán chạy nhất theo tháng
#         queryset = (
#             OrderItem.objects.filter(order__created_at__range=(start_date, end_date))
#             .values('product')
#             .annotate(total_sold=Sum('quantity'), total_revenue=Sum('price'))
#             .order_by('-total_sold')
#         )

#         #  Lấy thêm thông tin từ bảng Product và Category
#         best_sellers = [
#             BestSellingProduct(
#                 product=Product.objects.get(id=item['product']),
#                 category=Product.objects.get(id=item['product']).category.name,  # Lấy tên Category
#                 total_sold=item['total_sold'],
#                 total_revenue=item['total_revenue']
#             ) for item in queryset
#         ]

#         return best_sellers

#     def product_link(self, obj):
#         """Tạo link đến trang chi tiết sản phẩm"""
#         return format_html('<a href="/admin/app_name/product/{}/">{}</a>', obj.product.id, obj.product.name)

#     product_link.short_description = "Product"

#     def category(self, obj):
#         """Hiển thị danh mục của sản phẩm"""
#         return obj.category

# # Đăng ký Model Ảo vào Django Admin
# admin.site.register(BestSellingProduct, BestSellingProductAdmin)



























# ================== san pham =====================
# from django.contrib import admin
# from django.utils.translation import gettext_lazy as _
# class IsMainFilter(admin.SimpleListFilter):
#     title = _('Sản phẩm chính')  # Nhãn của bộ lọc
#     parameter_name = 'is_main'

#     def lookups(self, request, model_admin):
#         return [
#             ('yes', _('Có')),
#             ('no', _('Không')),
#         ]

#     def queryset(self, request, queryset):
#         if self.value() == 'yes':
#             return queryset.filter(is_main=True)
#         if self.value() == 'no':
#             return queryset.filter(is_main=False)
#         return queryset

# class ProductAdmin(admin.ModelAdmin):
#     list_filter = (IsMainFilter,)  # Thay vì ('is_main',)