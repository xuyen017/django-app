from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.db.models import Sum, F
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# Bảng Customer (Khách hàng)
class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)  # Mã khách hàng (Khóa chính, tự động tăng)
    name = models.CharField(max_length=100)  # Tên khách hàng
    email = models.EmailField(unique=True)  # Email của khách hàng (unique, không trùng)
    password = models.CharField(max_length=100)  # Mật khẩu của khách hàng
    phone = models.CharField(max_length=15)  # Số điện thoại của khách hàng
    address = models.TextField()  # Địa chỉ của khách hàng
    created_at = models.DateTimeField(auto_now_add=True)  # Thời gian tạo tài khoản khách hàng

    def __str__(self):
        return self.name
    class Meta:
        verbose_name ="khách hàng"
        verbose_name_plural = "Khách hàng"

# Bảng Category (Danh mục)
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)  # Mã danh mục (Khóa chính, tự động tăng)
    category_name = models.CharField(max_length=100)  # Tên danh mục 

    def __str__(self):
        return self.category_name
    class Meta:
        verbose_name ="Danh mục sản phẩm"
        verbose_name_plural = "Danh mục sản phẩm"
# Bảng Payment (thanh toán)
class Payment(models.Model):
    PAYMENT_CHOICES = [
        ('CASH', 'Tiền mặt nhận hàng'),
        ('BANK_TRANSFER', 'Chuyển khoản ngân hàng'),
        ('ORTHER', 'Thẻ tín dụng'),
    ]
    
    payment_id = models.AutoField(primary_key=True)  # Mã thanh toán
    payment_name = models.CharField(
        max_length=100,
        choices=PAYMENT_CHOICES,
        default='CASH',  # Giá trị mặc định là "Tiền mặt"
    )
    
    def __str__(self):
        return self.get_payment_name_display()
  

# Bảng Supplier (Nhà cung cấp)
class Supplier(models.Model):
    supplier_id = models.AutoField(primary_key=True)  # Mã nhà cung cấp (Khóa chính, tự động tăng)
    name = models.CharField(max_length=100, verbose_name = "Tên")  # Tên nhà cung cấp
    email = models.EmailField()  # Email của nhà cung cấpg
    password = models.CharField(max_length=100)  # Mật khẩu của nhà cung cấp
    phone = models.CharField(max_length=15, verbose_name = "Số điện thoại")  # Số điện thoại của nhà cung cấp
    address = models.TextField(verbose_name = "Địa chỉ")  # Địa chỉ của nhà cung cấp

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "Nhà cung cấp"
        verbose_name_plural = "Nhà cung cấp"

class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    created_at = models.DateField(auto_now_add=True)
    is_main = models.BooleanField(default=False, verbose_name="Sản phẩm chính")
    def clean(self):
         # Kiểm tra xem sản phẩm có cùng tên đã tồn tại chưa (trừ chính nó)
        if Product.objects.filter(name=self.name).exclude(product_id=self.product_id).exists():
            raise ValidationError('Sản phẩm đã tồn tại với tên này.')
        if self.price <0:
           raise ValidationError('giá bán ko được nhỏ hơn 0đ')
    def total_quantity_imported(self):
        # Tính tổng số lượng đã nhập từ StockInvoiceDetail
        total_quantity = StockInvoiceDetail.objects.filter(product=self).aggregate(
            total=Sum('quantity')
        )['total']
        return total_quantity or 0  # Trả về 0 nếu không có sản phẩm nào
    def total_quantity_ordered(self):
        # Tính tổng số lượng đã được đặt từ các đơn hàng
        total_quantity = OrderDetail.objects.filter(product=self).aggregate(total=Sum('quantity'))['total']
        return total_quantity or 0  # Trả về 0 nếu không có đơn hàng nào

    def available_stock(self):
        # Số lượng còn lại trong kho = tổng số lượng đã nhập - tổng số lượng đã đặt
        return self.total_quantity_imported() - self.total_quantity_ordered()
    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "Sản phẩm"
        verbose_name_plural = "Sản phẩm"
def upload_to(instance, filename):
    return f'products/{instance.product.product_id}/{filename}'
class ProductImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=upload_to, verbose_name=_("Product Image"), default='')
    is_main = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.product.name} - {'Main' if self.is_main else 'Additional'}"


    
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Đang đợi xác nhận'),
        ('confirmed', 'Xác nhận thành công, đang vận chuyển'),
        ('completed', 'Đã hoàn thành'),
        ('refund','Hoàn trả đơn hàng'),
        ('confirmrefund', 'Đã hoàn trả thành công'),
        ('cancellation', 'Đang hủy đơn hàng'),
        ('confirmcancellation', 'Xác nhận hủy đơn hàng'),      
    ]
    order_id = models.AutoField(primary_key=True)  # Mã đơn hàng (tự động tăng)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)  # Liên kết với bảng Customer
    order_date = models.DateTimeField(auto_now_add=True)  # Ngày giờ tạo đơn hàng
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='pending',  # Trạng thái mặc định là "Đang đợi xác nhận"
    )
    payment_method = models.ForeignKey(Payment, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Tổng số tiền đơn hàng
    shipping_address = models.CharField(max_length=255, blank=True, null=True)

    @property
    def get_cart_product(self):
        total = sum([item.quantity for item in self.order_details.all()])
        return total

    @property
    def get_cart_total(self):
        total = sum([item.get_total for item in self.order_details.all()])
        return total
    def calculate_total_amount(self):
        return sum(
            detail.product.price * detail.quantity
            for detail in self.order_details.all()
            if detail.product.price is not None
        )
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Lưu trước để tạo primary key
        # Logic liên quan đến mối quan hệ
        if self.pk:  # Chỉ chạy nếu Order đã có ID
            self.total_amount = self.calculate_total_amount()
            super().save(update_fields=['total_amount'])  # Lưu lần nữa nếu cần
    def __str__(self):
        return f"Order #{self.order_id} - {self.customer.name}"
    class Meta:
        verbose_name = "Đơn hàng"
        verbose_name_plural = "Đơn hàng"

# Bảng OrderDetails (Chi tiết đơn hàng)
class OrderDetail(models.Model):
    order_item_id = models.AutoField(primary_key=True)  # Mã chi tiết đơn hàng (Khóa chính, tự động tăng)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_details')  # Liên kết với bảng Order
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # Liên kết với bảng Product
    quantity = models.IntegerField()  # Số lượng sản phẩm trong đơn hàng
    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("Số lượng không được âm.")
        
        total_imported = self.product.total_quantity_imported()
        if self.quantity > total_imported:
            raise ValidationError(f"Số lượng đặt hàng ({self.quantity}) lớn hơn tổng số lượng đã nhập ({total_imported}).")
    @property
    def get_total(self):
        total = self.product.price * self.quantity
        return total
    def __str__(self):
        return f"Item {self.product.name} in Order #{self.order.order_id}"
    # Signal: Cập nhật total_amount khi thêm hoặc sửa OrderDetail

@receiver(post_save, sender=OrderDetail)
def update_order_total(sender, instance, **kwargs):
    order = instance.order
    order.total_amount = order.calculate_total_amount()
    order.save()

@receiver(post_delete, sender=OrderDetail)
def update_order_total_on_delete(sender, instance, **kwargs):
    order = instance.order
    order.total_amount = order.calculate_total_amount()
    order.save()


class StockInvoice(models.Model):
    invoice_id = models.AutoField(primary_key=True)  # Mã phiếu nhập kho (Khóa chính, tự động tăng)
    name = models.CharField(max_length=255)
    invoice_date = models.DateTimeField(auto_now_add=True)  # Ngày tạo phiếu nhập kho
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Tổng giá trị phiếu nhập kho

    def save(self, *args, **kwargs):
        if self.pk:  # Chỉ tính tổng tiền nếu đã tồn tại
            self.total_amount = sum(
                item.unit_price * item.quantity
                for item in self.stockinvoicedetail_set.all()
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice #{self.invoice_id}"
    class Meta:
        verbose_name = "Phiếu nhập"
        verbose_name_plural = "Phiếu nhập"
# Bảng StockInvoiceDetails (Chi tiết phiếu nhập kho)
class StockInvoiceDetail(models.Model):
    invoice_item_id = models.AutoField(primary_key=True)  # Mã chi tiết phiếu nhập kho (Khóa chính, tự động tăng)
    invoice = models.ForeignKey(StockInvoice, on_delete=models.CASCADE)  # Liên kết với bảng StockInvoice
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # Liên kết với bảng Product
    quantity = models.IntegerField()  # Số lượng sản phẩm trong phiếu nhập
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # Giá nhập của sản phẩm
    expiration_date = models.DateField(null=True, blank=True)  # Hạn sử dụng của sản phẩm trong phiếu nhập

    def clean(self):
        # Giá nhập phải nhỏ hơn giá bán
        if self.unit_price >= self.product.price:
            raise ValidationError("Giá nhập phải nhỏ hơn giá bán.")
        
        # Hạn sử dụng phải sau ngày hiện tại (nếu được cung cấp)
        if self.expiration_date and self.expiration_date <= now().date():
            raise ValidationError("Hạn sử dụng phải là ngày trong tương lai.")
        
        # Số lượng không được âm
        if self.quantity < 0:
            raise ValidationError("Số lượng không được âm.")

    def __str__(self):
        return f"Item {self.product.name} in Invoice #{self.invoice.invoice_id}"