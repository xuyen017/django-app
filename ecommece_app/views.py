from .models import *
from django.shortcuts import render, redirect, get_object_or_404
from .forms import *
from django.contrib import messages

def checkout(request):
    email = request.session.get('email')
    customer = Customer.objects.filter(email=email).first()
    if not customer:
        customer = Customer.objects.order_by('customer_id').first()
    payment_methods = Payment.objects.all()
    # Xử lý khi người dùng submit form
    if request.method == 'POST':
        address = request.POST.get("address")
        payment_methods_id = request.POST.get("payment_method")
        if not address or not payment_methods_id:
            messages.error(request, "Vui lòng điền đầy đủ thông tin")
            return redirect("Checkout")
        # cập nhật phương thức thanh toán cho đơn hàng
        payment_method = Payment.objects.filter(payment_id=payment_methods_id).first()
        order = Order.objects.create(
            customer=customer,
            status="pending",
            payment_method=payment_method,
            shipping_address=address
        )
        # Lưu order_id vào session để dùng trong trang QR
        request.session["order_id"] = order.order_id
        # Lấy giỏ hàng từ session
        cart = request.session.get('cart', {})
        # Kiểm tra và thêm sản phẩm vào đơn hàng
        for product_id, quantity in cart.items():
            try:
                product = Product.objects.get(product_id=product_id)
                
                if product.available_stock() < quantity:  # Kiểm tra tồn kho
                    messages.error(request, f"Sản phẩm {product.name} không đủ số lượng trong kho!")
                    return redirect("cart")

                # Thêm sản phẩm vào OrderDetail
                OrderDetail.objects.create(order=order, product=product, quantity=quantity)

            except Product.DoesNotExist:
                messages.error(request, f"Sản phẩm {product_id} không tồn tại!")
                return redirect("cart")

        # Cập nhật tổng tiền đơn hàng
        order.total_amount = order.calculate_total_amount()
        order.save()

        # Xóa giỏ hàng sau khi đặt hàng thành công
        request.session["cart"] = {}
        # **Xử lý điều hướng khi chọn phương thức thanh toán**
        if payment_method and payment_method.payment_name in ["BANK_TRANSFER", "ORTHER"]:
            return redirect('qr_payment')  # Chuyển qua trang mã QR

        messages.success(request, "Đặt hàng thành công!")
        return redirect("home")
    # Xử lý hiển thị giỏ hàng
    cart = request.session.get('cart', {})
    product_ids = list(cart.keys())
    products_dict = {p.product_id: p for p in Product.objects.filter(product_id__in=product_ids)} if product_ids else {}

    items = []
    total_price = 0
    total_quantity = 0

    for product_id, quantity in cart.items():
        product = products_dict.get(int(product_id))
        if product:
            total_price += product.price * quantity
            total_quantity += quantity
            items.append({'product': product, 'quantity': quantity, 'total': product.price * quantity})
            main_image = product.images.filter(is_main=True).first()
            product.main_image_url = main_image.image.url if main_image else 'app/images/banner/b1.jpg'

    context = {
        "customer": customer,
        "items": items,
        "payment_methods": payment_methods,
        "cart_total": total_price,
        'total_quantity': total_quantity
    }

    return render(request, "checkout.html", context)
def qr_payment(request):
    order_id = request.session.get("order_id")

    if not order_id:
        messages.error(request, "Không tìm thấy đơn hàng để thanh toán!")
        return redirect("home")

    order = Order.objects.filter(order_id=order_id).first()

    if not order:
        messages.error(request, "Đơn hàng không tồn tại!")
        return redirect("home")

    return render(request, "qr_payment.html", {
        "order": order,
        "total": order.total_amount
    })
def add_to_cart(request):
    if request.method == 'POST':
        # Lấy product_id từ POST request
        product_id = request.POST.get('product_id')
        if not product_id:
            messages.error(request, "Product ID is missing!")
            return redirect('home')

        # Lấy sản phẩm từ database
        try:
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            messages.error(request, "Product not found!")
            return redirect('home')

        # Kiểm tra số lượng trong kho (Dùng phương thức available_stock() thay vì total_quantity_imported())
        available_stock = product.available_stock()  # Lấy số lượng có sẵn trong kho

        # Lấy giỏ hàng từ session
        cart = request.session.get('cart', {})

        # Kiểm tra nếu sản phẩm đã có trong giỏ và số lượng không đủ
        if product_id in cart:
            if cart[product_id] + 1 > available_stock:  # Kiểm tra nếu thêm vào giỏ vượt quá kho
                messages.error(request, f"Không đủ sản phẩm {product.name} trong kho để thêm vào giỏ hàng.")
                return redirect('home')
            cart[product_id] += 1
        else:
            if 1 > available_stock:  # Kiểm tra nếu giỏ hàng không đủ sản phẩm
                messages.error(request, f"Không đủ sản phẩm {product.name} trong kho để thêm vào giỏ hàng.")
                return redirect('home')
            cart[product_id] = 1

        # Lưu giỏ hàng vào session
        request.session['cart'] = cart

        # Hiển thị thông báo và quay lại trang home
        messages.success(request, f"{product.name} đã được thêm vào giỏ hàng!")
        return redirect('home')

    return redirect('home')
def cart(request):
    # Lấy giỏ hàng từ session
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Giỏ hàng của bạn không có sản phẩm nào!")
        return redirect('home')  

    # Lấy danh sách sản phẩm từ cơ sở dữ liệu dựa trên product_id
    product_ids = list(cart.keys())
    products_dict = {}
    if product_ids:
        products_dict = {product.product_id: product for product in Product.objects.filter(product_id__in=product_ids)}
    for product_id, product in products_dict.items():
        main_image = product.images.filter(is_main=True).first()
        product.main_image_url = main_image.image.url if main_image else 'app/images/banner/b1.jpg'
    # Tính tổng số lượng và tổng giá trị giỏ hàng
    items = []
    total_quantity = 0
    total = 0
    for product_id, quantity in cart.items():
        product = products_dict.get(int(product_id))
        if product:
            total += product.price * quantity
            total_quantity += quantity
            items.append({'product': product, 'quantity': quantity, 'total': product.price * quantity})

    context = {
        'items': items,
        'cart': cart,
        'total': total,
        'total_quantity':total_quantity
    }
    
    return render(request, 'cart.html', context)
def home(request):

    products = Product.objects.filter(is_main=True)
    categories = Category.objects.all()
    suppliers = Supplier.objects.all()

    # Thêm thuộc tính `main_image_url` vào từng sản phẩm
    for product in products:
        main_image = product.images.filter(is_main=True).first()
        product.main_image_url = main_image.image.url if main_image else 'app/images/banner/b1.jpg'

    context = {'products': products, 'categories': categories, 'suppliers': suppliers}
    return render(request, 'home.html', context)
def search(request):
    query = request.GET.get('q', '')  # Lấy từ khóa tìm kiếm từ query string
    products = Product.objects.all()

    if query:
        # Tìm kiếm gần đúng (tên sản phẩm hoặc mô tả có chứa từ khóa)
        products = products.filter(name__icontains=query) | products.filter(description__icontains=query)
    for product in products:
        main_image = product.images.filter(is_main=True).first()
        product.main_image_url = main_image.image.url if main_image else 'app/images/banner/b1.jpg'
    context = {
        'products': products,
        'query': query,
    }
    return render(request, 'search.html', context)
def register(request):
    if request.method == 'POST':
        form = CustomerRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  
    else:
        form = CustomerRegisterForm()

    return render(request, 'register.html', {'form': form})
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            # Kiểm tra user tồn tại
            customer = Customer.objects.get(email=email)

            # Kiểm tra mật khẩu
            if password == customer.password:
                # Lưu thông tin người dùng vào session
                request.session['name'] = customer.name
                request.session['email'] = customer.email

                next_url = request.GET.get('next', 'home')  # Mặc định chuyển hướng về 'home' nếu không có tham số 'next'
                return redirect(next_url)
            else:
                messages.error(request, 'Sai mật khẩu.')
        except Customer.DoesNotExist:
            messages.error(request, 'Email không tồn tại. Vui lòng đăng ký tài khoản!')

    return render(request, 'login.html')
def logout_view(request):
    # Xóa toàn bộ session
    request.session.flush()

    # Chuyển hướng về trang đăng nhập hoặc trang chủ
    return redirect('home')  # 'login' là tên URL của trang đăng nhập
def profile(request):
    # Kiểm tra người dùng đã đăng nhập chưa
    if 'email' not in request.session:
        # Nếu chưa đăng nhập, chuyển hướng về trang đăng nhập
        return redirect('login')

    # Lấy thông tin từ session
    user_email = request.session.get('email')

    # Lấy thông tin người dùng từ database
    try:
        customer = Customer.objects.get(email=user_email)
    except Customer.DoesNotExist:
        messages.error(request, 'Người dùng không tồn tại.')
        return redirect('logout')

    if request.method == 'POST':
        form = ProfileForm(request.POST)
        
        if form.is_valid():
            # Cập nhật thông tin địa chỉ và số điện thoại
            new_phone = form.cleaned_data['phone']
            new_address = form.cleaned_data['address']

            customer.phone = new_phone
            customer.address = new_address
            customer.save()

            messages.success(request, 'Thông tin cá nhân đã được cập nhật.')
            # Cập nhật session nếu có thay đổi email
            request.session['email'] = customer.email
    else:
        # Hiển thị form với dữ liệu hiện tại của người dùng
        form = ProfileForm(initial={'phone': customer.phone, 'address': customer.address})

    return render(request, 'profile.html', {
        'form': form,
        'customer': customer
    })
def order_view(request):
    
    # Kiểm tra người dùng đã đăng nhập chưa
    if 'email' not in request.session:
        return redirect('login')

    # Lấy thông tin từ session
    user_email = request.session.get('email')

    try:
        customer = Customer.objects.get(email=user_email)
    except Customer.DoesNotExist:
        messages.error(request, 'Người dùng không tồn tại.')
        return redirect('logout')

     # Lấy tất cả đơn hàng của khách hàng trừ đơn có trạng thái confirmcancellation
    orders = Order.objects.filter(customer=customer).exclude(status='confirmcancellation')

    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        try:
            order = Order.objects.get(order_id=order_id, customer=customer)
            if order.status == 'pending':  # Chỉ cho phép hủy đơn hàng có trạng thái "Đang đợi xác nhận"
                order.status = 'cancellation'
                order.save()
                messages.success(request, 'Đơn hàng đã được hủy. Đợi admin xác nhận.')
            elif order.status == 'completed':  # Chỉ xử lý khi trạng thái là 'completed'
                order.status = 'refund'
                order.save()
                messages.success(request, 'Đơn hàng đã được hoàn trả. Đợi admin xác nhận.')
            else:
                messages.error(request, 'Không thể hủy đơn hàng với trạng thái hiện tại.')
            
        except Order.DoesNotExist:
            messages.error(request, 'Đơn hàng không tồn tại.')

    return render(request, 'orders.html', {
        'customer': customer,
        'orders': orders,
    })
def category(request):
    # Lấy tất cả các danh mục
    categories = Category.objects.all()

    # Lấy `category_id` từ query string
    active_category = request.GET.get('category_id', '')

    # Nếu có `category_id`, lọc sản phẩm theo danh mục đó
    products = Product.objects.filter(category_id=active_category) if active_category else []
    for product in products:
        main_image = product.images.filter(is_main=True).first()
        product.main_image_url = main_image.image.url if main_image else 'app/images/banner/b1.jpg'
    context = {
        'categories': categories,
        'products': products,
        'active_category': active_category,
    }
    return render(request, 'category.html', context)
def supplier(request):
    # Lấy tất cả các danh mục
    suppliers = Supplier.objects.all()

    # Lấy `category_id` từ query string
    active_category = request.GET.get('supplier_id', '')

    # Nếu có `category_id`, lọc sản phẩm theo danh mục đó
    products = Product.objects.filter(supplier_id=active_category) if active_category else []
    for product in products:
        main_image = product.images.filter(is_main=True).first()
        product.main_image_url = main_image.image.url if main_image else 'app/images/banner/b1.jpg'
    context = {
        'suppliers': suppliers,
        'products': products,
        'active_category': active_category,
    }
    return render(request, 'supplier.html', context)
def product_detail(request):
   
    product_id = request.GET.get('product_id', None)

    # Kiểm tra nếu product_id không có hoặc không phải là số hợp lệ
    if not product_id or not product_id.isdigit():
        return render(request, 'product_not_found.html')  # Hoặc trang lỗi bạn muốn

    # Chuyển product_id thành số nguyên
    product_id = int(product_id)

    # Lọc sản phẩm theo product_id
    try:
        product = Product.objects.get(product_id=product_id)
    except Product.DoesNotExist:
        return render(request, 'product_not_found.html')  # Nếu không tìm thấy sản phẩm

    # Lấy tất cả hình ảnh liên quan đến sản phẩm
    images = product.images.all()  # Đây sẽ trả về tất cả các ProductImage liên quan đến sản phẩm

    context = {
        'product': product,
        'images': images,  # Danh sách các đối tượng ProductImage
    }

    return render(request, 'product_detail.html', context)
def update_cart(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))  # Mặc định là 1 nếu không có

        # Kiểm tra sản phẩm có tồn tại không
        try:
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            messages.error(request, "Sản phẩm không tồn tại.")
            return redirect('cart')

        # Gọi phương thức available_stock nếu cần (chú ý dấu ngoặc đơn nếu là method)
        available_stock = product.available_stock()  # Nếu đây là phương thức

        # Lấy giỏ hàng từ session
        cart = request.session.get('cart', {})

        if quantity <= 0:
            # Xóa sản phẩm khỏi giỏ hàng nếu số lượng bằng 0
            if product_id in cart:
                del cart[product_id]
                request.session['cart'] = cart
                messages.success(request, f"Đã xóa {product.name} khỏi giỏ hàng.")
            else:
                messages.error(request, f"Sản phẩm {product.name} không có trong giỏ hàng.")
        elif quantity > available_stock:
            messages.error(request, f"Số lượng sản phẩm {product.name} vượt quá kho ({available_stock}).")
        else:
            # Cập nhật số lượng sản phẩm
            cart[product_id] = quantity
            request.session['cart'] = cart
            messages.success(request, f"Số lượng {product.name} đã được cập nhật.")

        return redirect('cart')

    return redirect('cart')
def supplier_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            # Kiểm tra user tồn tại
            supplier = Supplier.objects.get(email=email)

            # Kiểm tra mật khẩu
            if password == supplier.password:
                # Lưu thông tin người dùng vào session
                request.session['supplier_id'] = supplier.supplier_id
                request.session['name'] = supplier.name
                request.session['email'] = supplier.email

                return redirect('supplier_dashboard')  # Chuyển đến dashboard của supplier
            else:
                messages.error(request, 'Sai mật khẩu. Vui lòng thử lại!')
        except Supplier.DoesNotExist:
            messages.error(request, 'Email không tồn tại. Vui lòng đăng ký tài khoản!')
    
    return render(request, 'supplier_login.html')
def supplier_dashboard(request):
    if 'supplier_id' not in request.session:
        return redirect('supplier_login')

    supplier_id = request.session.get('supplier_id')
    products = Product.objects.filter(supplier_id=supplier_id, is_main=False)
    return render(request, 'supplier_dashboard.html', {'products': products})
def add_product(request):
    if 'supplier_id' not in request.session:
        return redirect('supplier_login')

    categories = Category.objects.all()

    if request.method == 'POST':
        supplier_id = request.session.get('supplier_id')
        supplier = Supplier.objects.get(supplier_id=supplier_id)

        name = request.POST.get('name')
        category_id = request.POST.get('category')
        description = request.POST.get('description')
        price = request.POST.get('price')

        if not category_id:
            return render(request, 'add_product.html', {'categories': categories, 'error': 'Vui lòng chọn loại sản phẩm!'})

        category = Category.objects.get(category_id=category_id)

        Product.objects.create(
            name=name,
            category=category,
            description=description,
            price=price,
            supplier=supplier,
            is_main=False
        )
        return redirect('supplier_dashboard')

    return render(request, 'add_product.html', {'categories': categories})
def edit_product(request):
    if request.method == 'POST' and 'product_id' in request.POST:
        request.session['product_id'] = request.POST.get('product_id')

    if 'product_id' not in request.session:
        return redirect('supplier_dashboard')

    product_id = request.session['product_id']
    product = get_object_or_404(Product, product_id=product_id)
    categories = Category.objects.all()

    if request.method == 'POST' and 'name' in request.POST:
        product.name = request.POST.get('name')
        category_id = request.POST.get('category')
        product.category = Category.objects.get(category_id=category_id)
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.save()
        return redirect('supplier_dashboard')

    return render(request, 'edit_product.html', {'product': product, 'categories': categories})
def delete_product(request):
    if request.method == 'POST' and 'product_id' in request.POST:
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, product_id=product_id)
        product.delete()
    return redirect('supplier_dashboard')
