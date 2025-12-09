from decimal import Decimal
from django.shortcuts import render,redirect
from Accounts.views import signin
from django.views.decorators.cache import never_cache
from Accounts.views import account_details
from Product.models import Variants
from .models import Custom_User as User,Wishlist,Cart,Address,DeliveryAddress,Orders,Order_items, Wallet, Transactions
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from datetime import timedelta
from django.conf import settings
from admin_panel.models import Brand_offer, Product_offer
from admin_panel.models import Coupon,Coupon_usage
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from datetime import date
from django.templatetags.static import static
from django.contrib.auth.decorators import login_required
import razorpay


from django.db import transaction


# Create your views here.
def create_wallet(user):
    wallet = Wallet.objects.filter(user=user)
    if len(wallet) == 0 :
        print('hi')
        wallet = Wallet.objects.create(user = user, balence = 0.00)


def view_wallet(request):
    create_wallet(request.user)
    wallet = Wallet.objects.get(user=request.user)
    transactions = Transactions.objects.filter(wallet=wallet).order_by('-id')

    return render(request,'wallet.html',{'wallet':wallet,'transactions':transactions})        
@login_required(login_url='signin')
def add_to_cart(request, variant_id):
    user = request.user
    variant = Variants.objects.get(pk=variant_id)
    

    #    Out of stock 
    if not variant.is_active or variant.quantity <= 0:
        return JsonResponse({
            'status': 'error',
            'message': 'This product is out of stock'
        })
    #  Offer logic 
    p_offers = Product_offer.objects.all()
    b_offers = Brand_offer.objects.all()
    offerd_product_ides = [p_offer.product.id for p_offer in p_offers]
    offerd_brand_ides = [b_offer.brand.id for b_offer in b_offers]

    if variant.product.id in offerd_product_ides:
        for offer in p_offers:
            if offer.product.id == variant.product.id:
                if variant.product.brand.id in offerd_brand_ides:
                    for b_offer in b_offers:
                        if b_offer.percentage > offer.percentage:
                            unit_price = float(variant.price) - (float(variant.price) * float(b_offer.percentage)) / 100
                        else:
                            unit_price = float(variant.price) - (float(variant.price) * float(offer.percentage)) / 100
                else:
                    unit_price = float(variant.price) - (float(variant.price) * float(offer.percentage)) / 100
    elif variant.product.brand.id in offerd_brand_ides:
        for offer in b_offers:
            if offer.brand.id == variant.product.brand.id:
                unit_price = float(variant.price) - (float(variant.price) * float(offer.percentage)) / 100
    else:
        unit_price = variant.price
  

    cart_item, created = Cart.objects.get_or_create(user=user, variant=variant, unit_price=unit_price)
    
    
    
    if not created:
        if cart_item.quantity < cart_item.variant.quantity:
            cart_item.quantity += 1
            cart_item.save()
            Wishlist.objects.filter(user=user, variant=variant).delete()
            return JsonResponse({'status': 'quantity_updated', 'message': 'Quantity updated in cart ✅'}, status=200)
        else:
            return JsonResponse({'status': 'max', 'message': 'Maximum stock reached ❌'}, status=200)
        
 
    return JsonResponse({'status': 'added', 'message': 'Product added to cart successfully 🛒'}, status=200)

def add_to_wishlist(request,variant_id):
    if request.user.is_authenticated:
        user = request.user
        variant = Variants.objects.get(pk=variant_id)
        
        if Wishlist.objects.filter(variant=variant, user=user).exists():
            return JsonResponse({'status': 'exists'}, status=200)
        
        Wishlist.objects.create(user=user, variant=variant)
        return JsonResponse({'status': 'added'}, status=200)
    else :
        return JsonResponse({'status': 'unauthenticated'})




@never_cache
def view_cart(request):
    if request.user.is_authenticated:
        user = request.user
        carts = Cart.objects.filter(user=user)
        p_offers = Product_offer.objects.all()
        b_offers = Brand_offer.objects.all()
        offerd_product_ides = [p_offer.product.id for p_offer in p_offers]
        offerd_brand_ides = [b_offer.brand.id for b_offer in b_offers]
        c_id =[]
        subtotal = 0
        for cart in carts:
            if cart.variant.product.id in offerd_product_ides:
                for offer in p_offers:
                    if float(cart.unit_price) != (float(cart.variant.price) - (float(cart.variant.price)*float(offer.percentage))/100):
                        cart.unit_price = (float(cart.variant.price) - (float(cart.variant.price)*float(offer.percentage))/100)
            elif cart.variant.product.brand.id in offerd_brand_ides :
                for offer in b_offers:
                    if float(cart.unit_price) != (float(cart.variant.price) - (float(cart.variant.price)*float(offer.percentage))/100):
                        cart.unit_price = (float(cart.variant.price) - (float(cart.variant.price)*float(offer.percentage))/100)
            else :
                if cart.unit_price != cart.variant.price:
                    cart.unit_price = cart.variant.price
                    cart.unit_price = float(cart.unit_price)
            cart.price = cart.quantity * cart.unit_price
            c_id.append(cart.id)
            subtotal += float(cart.price) 
        tax = (0.08/100) * float(subtotal)
        tax = round(tax, 2)
        total = float(subtotal) +tax 
        total = round(total, 2)
        request.session['carts'] = c_id
        request.session['subtotal'] = int(subtotal)
        request.session['tax'] =  int(tax)
        request.session['total'] =  int(total)
        
        return render(request,'cart.html',
                      {
                            'carts':carts,
                            'subtotal':subtotal,
                            'tax':tax,
                            'total':total,
                            'p_offers': p_offers,
                            'b_offers': b_offers,
                            'offerd_product_ides': offerd_product_ides,
                            'offerd_brand_ides': offerd_brand_ides,
                          })
    else:
        return redirect(signin)    

    
@never_cache
def wishlist(request):
    if request.user.is_authenticated:
        user = request.user
        wishlists = Wishlist.objects.filter(user=user)
        print(wishlists)
        p_offers = Product_offer.objects.all()
        b_offers = Brand_offer.objects.all()
        offerd_product_ides = [p_offer.product.id for p_offer in p_offers]
        offerd_brand_ides = [b_offer.brand.id for b_offer in b_offers]
        return render(request,'wishlist.html',
            {
            'wishlists':wishlists,
            'p_offers': p_offers,
            'b_offers': b_offers,
            'offerd_product_ides': offerd_product_ides,
            'offerd_brand_ides': offerd_brand_ides,
            })
    else:
        return redirect(signin)
    
def remove_from_wishlist(request,wishlist_id):
    wishlist = Wishlist.objects.get(pk=wishlist_id)
    wishlist.delete()
    return redirect('wishlist') 

def remove_from_cart(request,cart_id):
    cart = Cart.objects.get(pk=cart_id)
    cart.delete()
    return redirect(view_cart)

def plus_cart_quantity(request, cart_id):
    if request.user.is_authenticated:
        cart = Cart.objects.get(pk=cart_id)
        
        if cart.quantity < cart.variant.quantity :
            cart.quantity += 1
            cart.price = cart.quantity * cart.unit_price
            cart.save()
            carts = Cart.objects.filter(user=request.user)
            subtotal=0
            for c in carts:
                subtotal +=c.price
            request.session['subtotal'] = int(subtotal)
            tax = (0.08/100) * float(subtotal)
            total = float(subtotal) +tax
            request.session['tax'] =  int(tax)
            request.session['total'] =  int(total)
            return JsonResponse({
                'status': 'success',
                'quantity': cart.quantity,
                'price': cart.price,
                'subtotal': subtotal,
            }, status=200)
        return JsonResponse({'status': 'max'}, status=200)
    return JsonResponse({'status': 'unauthenticated'}, status=403)
def minus_cart_quantity(request, cart_id):
    if request.user.is_authenticated:
        cart = Cart.objects.get(pk=cart_id)
        if cart.quantity > 1:
            cart.quantity -= 1
            cart.price = cart.quantity * cart.unit_price
            cart.save()
            carts = Cart.objects.filter(user=request.user)
            subtotal=0
            for c in carts:
                subtotal +=c.price
            request.session['subtotal'] = int(subtotal)
            tax = (0.08/100) * float(subtotal)
            total = float(subtotal) +tax
            request.session['tax'] =  int(tax)
            request.session['total'] =  int(total)
            return JsonResponse({
                'status': 'success',
                'quantity': cart.quantity,
                'price': cart.price,
                'subtotal': subtotal,
                'total':subtotal+400
            }, status=200)
        
        return JsonResponse({'status': 'min_quantity'}, status=200)
    
    return JsonResponse({'status': 'unauthenticated'}, status=403)

def add_address(request):
    if request.method == 'POST':
        id = request.POST['id']
        if id != 'old':
            address = Address.objects.get(pk=id)
            state = request.POST['state']
            city = request.POST['city']
            place = request.POST['place']
            pin = request.POST['pin']
            road = request.POST['road']
            house_name = request.POST['house_name']
            landmark = request.POST['landmark']
            address.state=state
            address.city =city
            address.place =place
            address.pin =pin
            address.road =road
            address.house_name =house_name
            address.landmark =landmark
            address.city =city
            address.save()
        else :
            state = request.POST['state']
            district = request.POST['district']
            city = request.POST['city']
            place = request.POST['place']
            pin = request.POST['pin']
            road = request.POST['road']
            house_name = request.POST['house_name']
            landmark = request.POST['landmark']
            user = request.user
            address = Address.objects.create(state=state,district=district,city=city,place=place,pin=pin,road=road,house_name=house_name,landmark=landmark,user=user)
            address.save()
            messages.success(request, "Your Adress updated successfully!")
    return redirect(account_details)


from django.views.decorators.http import require_POST
@require_POST
def apply_coupon(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Please login'}, status=403)

    coupon_code = request.POST.get('coupon')
    total_price = request.POST.get('total_price')  # expect  total_before_discount value
    if not coupon_code:
        return JsonResponse({'success': False, 'message': 'Please provide coupon code'})

    try:
        total_before = Decimal(str(total_price))
    except Exception:
        return JsonResponse({'success': False, 'message': 'Invalid total'})

    # validate coupon
    try:
        coupon = Coupon.objects.get(code=coupon_code)
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid coupon'})

    # expiry and amount checks
    if coupon.expiry <= date.today():
        return JsonResponse({'success': False, 'message': 'Coupon expired'})

    if not (Decimal(str(coupon.min_amount)) <= total_before <= Decimal(str(coupon.max_amount))):
        return JsonResponse({'success': False, 'message': 'Coupon not applicable for this order amount'})

    # check coupon usage
    if Coupon_usage.objects.filter(user=user, coupon=coupon).exists():
        return JsonResponse({'success': False, 'message': 'Coupon already used by you'})

    # compute discount percentage
    discount_amount = (total_before * Decimal(str(coupon.percentage)) / Decimal('100')).quantize(Decimal('0.01'))

    final_total = (total_before - discount_amount).quantize(Decimal('0.01'))
    if final_total < 0:
        final_total = Decimal('0.00')

    # save to session floats for JSON
    request.session['discount'] = float(discount_amount)
    request.session['coupon_code'] = coupon.code
    request.session['final_total'] = float(final_total)
    request.session.modified = True

    return JsonResponse({
        'success': True,
        'total': float(final_total),
        'discount': float(discount_amount),
        'coupon_code': coupon.code
    })
@require_POST
def remove_coupon(request):
    request.session.pop('discount', None)
    request.session.pop('coupon_code', None)
    request.session.pop('final_total', None)
    request.session.modified = True
    return JsonResponse({'status': 'removed'})


def view_address(request, address_id):
    address =Address.objects.get(pk=address_id)
    return JsonResponse({
            'status': 'success',
            'state': address.state,
            'district': address.district,
            'city': address.city,
            'place': address.place,
            'pin': address.pin,
            'house_name': address.house_name,
            'landmark': address.landmark,
            'road': address.road,
            
        }, status=200)


def delete_address(request,address_id):
    address = Address.objects.get(pk=address_id)
    address.delete()
    messages.warning(request, "your address is deleted!")
    return redirect(account_details)

def update_profile_pic(request):
    if request.method == "POST" and request.FILES.get("profile_pic"):
        user = request.user
        user.profile_pic = request.FILES["profile_pic"]
        user.save()
        messages.success(request, "Profile picture updated successfully!")
    return redirect("account_details")

def checkout(request):
    user = request.user
    if not user.is_authenticated:
        return redirect('signin')   # signin view

    # fetch cart ids from session  tax ensure session keys exist
    c_id = request.session.get('carts', [])
    tax = request.session.get('tax', 0)  #might be float or Decimal
    delivery_charge = 50

    # fetch cart objects
    carts = [Cart.objects.get(pk=i) for i in c_id] if c_id else []

    # calculate subtotal and ensure unitprice and price are available on Cart
    subtotal_decimal = Decimal('0')
    for cart in carts:
        # ensure unitprice is present
        unit_price = Decimal(str(cart.unit_price)) if hasattr(cart, 'unit_price') else Decimal(str(cart.variant.price))
        line_total = unit_price * Decimal(str(cart.quantity))
        subtotal_decimal += line_total

    tax_decimal = Decimal(str(tax))
    delivery_decimal = Decimal(str(delivery_charge))

    total_before_discount = subtotal_decimal + tax_decimal + delivery_decimal

    # read discount and coupon from session tored as float — convert to Decimal
    coupon_code = request.session.get('coupon_code', None)
    discount_decimal = Decimal(str(request.session.get('discount', 0))) if coupon_code else Decimal('0')

    # final total
    final_total_decimal = total_before_discount - discount_decimal
    if final_total_decimal < 0:
        final_total_decimal = Decimal('0')

    # create Razorpay order (optional) and amount in paise
    # If you already created razorpay_order_id elsewhere, adjust accordingly.
    client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
    razorpay_amount_paise = int((final_total_decimal * 100).to_integral_value())  # integer paise

    # create razorpay order to get order_id
    try:
        razorpay_order = client.order.create({
            "amount": razorpay_amount_paise,
            "currency": "INR",
            "payment_capture": 1
        })
        razorpay_order_id = razorpay_order.get('id')
    except Exception:
        razorpay_order_id = None

    try:
        wallet = Wallet.objects.get(user=user)
    except Wallet.DoesNotExist:
        wallet = None    

    # save numeric values into session as floats (JSON-serializable)
    request.session['subtotal'] = float(subtotal_decimal)
    request.session['tax'] = float(tax_decimal)
    request.session['delivery_charge'] = float(delivery_decimal)
    request.session['total_before_discount'] = float(total_before_discount)
    request.session['discount'] = float(discount_decimal)
    request.session['final_total'] = float(final_total_decimal)
    request.session.modified = True

    context = {
        'user': user,
        'addresses': Address.objects.filter(user=user),
        'carts': carts,
        'subtotal': float(subtotal_decimal),
        'tax': float(tax_decimal),
        'delivery_charge': float(delivery_decimal),
        'total_before_discount': float(total_before_discount),
        'discount': float(discount_decimal),
        'total': float(final_total_decimal),
        'amount': razorpay_amount_paise,           # paise, integer
        'razorpay_order_id': razorpay_order_id,
        'RAZORPAY_API_KEY': settings.RAZORPAY_API_KEY,
        # coupons available 
        'coupons': Coupon.objects.filter(expiry__gt=date.today(), min_amount__lte=total_before_discount, max_amount__gte=total_before_discount),
        'wallet':wallet
    }

    return render(request, 'check_out.html', context)

def susses(request):
    return render(request,'susses.html')


def failed(request):
    return render(request,'failed.html')




@require_POST
def order(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({'status': 'unauthenticated'}, status=403)

    # load session values floats stored
    subtotal = Decimal(str(request.session.get('subtotal', 0)))
    tax = Decimal(str(request.session.get('tax', 0)))
    delivery_charge = Decimal(str(request.session.get('delivery_charge', 0)))
    discount = Decimal(str(request.session.get('discount', 0)))
    final_total = Decimal(str(request.session.get('final_total', subtotal + tax + delivery_charge)))

    c_id = request.session.get('carts', [])
    carts = [Cart.objects.get(pk=i) for i in c_id] if c_id else []

    # address fields
    state = request.POST.get('state')
    district = request.POST.get('district')
    city = request.POST.get('city')
    place = request.POST.get('place')
    pin = request.POST.get('pin')
    road = request.POST.get('road')
    house_name = request.POST.get('house_name')
    landmark = request.POST.get('landmark')
    name = request.POST.get('name')
    phone = request.POST.get('phone')

    pymd = request.POST.get('pymd')  # payment method
    pyst = request.POST.get('pyst', 'pending')  # payment status

    save_address = request.POST.get('save_address', 'no')
    if save_address == 'yes':
        Address.objects.create(
            user=user, state=state, district=district, city=city, place=place,
            pin=pin, road=road, house_name=house_name, landmark=landmark
        )

    delivery_address = DeliveryAddress.objects.create(
        state=state, district=district, city=city, place=place, pin=pin,
        road=road, house_name=house_name, landmark=landmark, name=name, phone=phone
    )

    try:
        with transaction.atomic():
            # lock variants
            locked = []
            for cart in carts:
                variant = Variants.objects.select_for_update().get(id=cart.variant.id)
                locked.append((variant, cart))

            # stock checks
            for variant, cart in locked:
                if not variant.is_active or variant.quantity < cart.quantity:
                    return JsonResponse({'status': 'failed', 'message': f'{variant.product.name} out of stock'})

            # wallet payment handling
            if pymd == 'wallet payment':
                wallet = Wallet.objects.select_for_update().get(user=user)
                if Decimal(str(wallet.balence)) < final_total:
                    return JsonResponse({'status': 'failed', 'message': 'Insufficient wallet balance'})
                wallet.balence = float(Decimal(str(wallet.balence)) - final_total)
                wallet.save()
                pyst = 'done'

            # create order object save decimal to float only in session model fields can be Decimal
            order = Orders.objects.create(
                user=user,
                delivery_address=delivery_address,
                pyment_method=pymd,
                pyment_status=pyst,
                subtotal=subtotal,
                tax=tax,
                discount=discount,
                total=final_total
            )

            # wallet transaction record
            if pymd == 'wallet payment':
                Transactions.objects.create(order=order, wallet=wallet, type='debit', amount=final_total)

            # create items and reduce stock
            for variant, cart in locked:
                Order_items.objects.create(
                    order=order,
                    variant=variant,
                    unit_price=Decimal(str(cart.unit_price)),
                    price=Decimal(str(cart.unit_price)) * Decimal(str(cart.quantity)),
                    quantity=cart.quantity,
                    status='Order placed',
                    user=user
                )
                variant.quantity = variant.quantity - cart.quantity
                variant.save()

            # mark coupon usage if coupon applied
            coupon_code = request.session.get('coupon_code', None)
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(code=coupon_code)
                    Coupon_usage.objects.create(user=user, coupon=coupon)
                except Coupon.DoesNotExist:
                    pass

            # clear cart and  session coupon keys
            Cart.objects.filter(user=user).delete()
            request.session.pop('carts', None)
            for key in ['discount', 'coupon_code', 'final_total', 'total_before_discount']:
                request.session.pop(key, None)
            request.session.modified = True

            return JsonResponse({'status': 'success', 'amount': float(final_total)})

    except Exception as e:
        return JsonResponse({'status': 'failed', 'message': str(e)})

@never_cache
def view_orders(request):
    if request.user.is_authenticated:
        order_items = Order_items.objects.filter(user=request.user).order_by('-id')
        return render(request,'orders.html',{'order_items':order_items})
    else:
        return redirect(signin)
    
@never_cache
def order_details(request,orderitem_id):
    if request.user.is_authenticated:
        order_item = Order_items.objects.get(pk=orderitem_id)
        order_item.order.delivery_date = order_item.order.order_date + timedelta(days=14)  
        order_item.save()
        return render(request,'order_details.html',{'order_item':order_item})
    else:
        return redirect(signin)
    


def cancel_order(request,order_item_id):
    create_wallet(request.user)
    order_item = Order_items.objects.get(pk=order_item_id)
    if order_item.order.pyment_status == 'done':
        wallet = Wallet.objects.get(user=request.user)
        amount = float(order_item.price) - float(order_item.order.discount)
        transaction = Transactions.objects.create(order_item=order_item, wallet=wallet, variant = order_item.variant, amount = amount)
        order_item.order.discount = 0
        wallet.balence = float(wallet.balence)
        wallet.balence += float(transaction.amount)
        order_item.order.save()
        wallet.save()
    order_item.status = 'cancelled'
    order_item.is_active = False
    variant = Variants.objects.get(pk=order_item.variant.id) 
    variant.quantity += order_item.quantity
    variant.save()
    order_item.save()
    return redirect(view_orders)

def return_order(request,order_item_id):
    create_wallet(request.user)
    order_item = Order_items.objects.get(pk=order_item_id)
    if order_item.order.pyment_status == 'done':
        wallet = Wallet.objects.get(user=request.user)
        amount = float(order_item.price) - float(order_item.order.discount)
        transaction = Transactions.objects.create(order_item=order_item, wallet=wallet, variant = order_item.variant, amount = amount)
        order_item.order.discount = 0
        wallet.balence = float(wallet.balence)
        wallet.balence += float(transaction.amount)
        order_item.order.save()
        wallet.save()
    if request.method=="POST":
        reason=request.POST.get("reson")
        order_item.return_reson=reason
        order_item.status = 'Return pending'
        order_item.save()
    return redirect(view_orders)



def retry_Payment(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        pyst = request.POST.get('pyst')
        orders = Orders.objects.get(pk=order_id)
        orders.pyment_status = pyst
        orders.save()
        return JsonResponse({
            'status': 'success',
            # 'razorpay_order_id': razorpay_order_id,
            'razorpay_key': settings.RAZORPAY_API_KEY,
            
        }, status=200)


def generate_invoice_pdf(request, order_item_id):
    order_item = Order_items.objects.get(id=order_item_id) 
    template_path = 'invoice.html' 
    context = {'order_item': order_item}

    # Render the template to a string
    template = get_template(template_path)
    html = template.render(context)

    # Create  response object
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="invoice.pdf"'

    # Generate the PDF
    pisa_status = pisa.CreatePDF(html, dest=response)

    # If theres an error show some fallback HTML
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response





def privacy_policy(request):
    return render(request, "privacy_policy.html")

def terms_conditions(request):
    return render(request, "terms_conditions.html")

def refund_policy(request):
    return render(request, "refund_policy.html")
















