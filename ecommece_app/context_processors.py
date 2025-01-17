def customer_visibility(request):
    if 'email' in request.session:
        return {
            'customer_not_login': 'hidden',
            'customers_login': 'show',
        }
    else:
        return {
            'customer_not_login': 'show',
            'customers_login': 'hidden',
        }
