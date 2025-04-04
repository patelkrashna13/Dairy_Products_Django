from django.db.models import Count,Q
from django.http import JsonResponse
from django.shortcuts import render , redirect
from django.views import View
import razorpay
from . models import Product,Customer,Cart,Payment,OrderPlaced
from . forms import CustomerRegistrationForm , CustomerProfileForm
from django.contrib import messages
from django.conf import settings


# Create your views here.
def home(req):
    return render(req,'app/home.html')

def about(req):
    return render(req,'app/about.html')

def contact(req):
    return render(req,'app/contact.html')

class CategoryView(View):
    def get(self,request,val):
         product = Product.objects.filter(category=val)
         title = Product.objects.filter(category=val).values('title')
         return render(request,"app/category.html",locals()) #locals are inbuilt function used to pass the value


class CategoryTitle(View):
    def get(self,request,val):
         product = Product.objects.filter(title=val)
         title = Product.objects.filter(category=product[0].category).values('title')
         return render(request,"app/category.html",locals())
    

class ProductDetail(View):
    def get(self,request,pk):
        product = Product.objects.get(pk=pk)
        return render(request,"app/productdetail.html",locals())
    
class CustomerRegistrationView(View):
    def get(self,request):
        form = CustomerRegistrationForm()
        return render(request,'app/customerregistration.html',locals())
    def post(self,request):
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Congratulations! User Register Successfully")
        else:
            messages.warning(request,"Invalid Input Data")
        return render(request, 'app/customerregistration.html', locals())
    

class ProfileView(View):
    def get(self,request):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return redirect('login')
            
        # Get existing customer profile data if any
        try:
            customer = Customer.objects.filter(user=request.user).first()
            # Pre-populate form with existing data if available
            if customer:
                form = CustomerProfileForm(instance=customer)
            else:
                form = CustomerProfileForm()
        except:
            form = CustomerProfileForm()
            
        # Calculate account statistics
        orders_count = OrderPlaced.objects.filter(user=request.user).count()
        saved_addresses = Customer.objects.filter(user=request.user).count()
        
        # Get recent orders
        recent_orders = OrderPlaced.objects.filter(user=request.user).order_by('-ordered_date')[:3]
        
        # Prepare context data
        context = {
            'form': form,
            'customer': customer,
            'orders_count': orders_count,
            'saved_addresses': saved_addresses,
            'recent_orders': recent_orders,
            'user': request.user
        }
        
        return render(request, 'app/profile.html', context)
        
    def post(self,request):
        form = CustomerProfileForm(request.POST)
        if form.is_valid():
            user = request.user
            # Check if user already has a profile
            existing_customer = Customer.objects.filter(user=user).first()
            
            # Get cleaned data
            name = form.cleaned_data['name']
            locality = form.cleaned_data['locality']
            city = form.cleaned_data['city']
            mobile = form.cleaned_data['mobile']
            state = form.cleaned_data['state']
            zipcode = form.cleaned_data['zipcode']
            
            if existing_customer:
                # Update existing profile
                existing_customer.name = name
                existing_customer.locality = locality
                existing_customer.city = city
                existing_customer.mobile = mobile
                existing_customer.state = state
                existing_customer.zipcode = zipcode
                existing_customer.save()
            else:
                # Create new profile
                reg = Customer(user=user,name=name,locality=locality,mobile=mobile,city=city,state=state,zipcode=zipcode)
                reg.save()
                
            messages.success(request,"Congratulations! Profile Saved Successfully")
        else:
            messages.warning(request,"Invalid Input Data")
            
        return redirect('profile')


def address(request):
    add=Customer.objects.filter(user=request.user)
    return render(request, 'app/address.html',locals())

def delete_address(request, address_id):
    if request.user.is_authenticated:
        try:
            address = Customer.objects.get(id=address_id, user=request.user)
            address.delete()
            messages.success(request, "Address deleted successfully!")
        except Customer.DoesNotExist:
            messages.error(request, "Address not found!")
        return redirect("address")
    else:
        return redirect("login")

class updateAddress(View):
    def get(self,request,pk):
        add = Customer.objects.get(pk=pk)
        form = CustomerProfileForm(instance=add)#all the data is fill automatically in update page
        return render(request, 'app/updateAddress.html',locals())
    def post(self,request,pk):
        form = CustomerProfileForm(request.POST)
        if form.is_valid():
            add = Customer.objects.get(pk=pk)
            add.name = form.cleaned_data['name']
            add.locality = form.cleaned_data['locality']
            add.city = form.cleaned_data['city']
            add.mobile = form.cleaned_data['mobile']
            add.state = form.cleaned_data['state']
            add.zipcode = form.cleaned_data['zipcode']
            add.save()
            messages.success(request,"Congratulations! Profile Updated Successfully")
        else:
            messages.warning(request,"Invalid Input Data")
        return redirect("address")

def add_to_cart(request):
    user=request.user
    product_id=request.GET.get('prod_id')
    product = Product.objects.get(id=product_id)
    Cart(user=user,product=product).save()
    return redirect("/cart")

def show_cart(request):
    user = request.user
    cart = Cart.objects.filter(user=user)
    amount = 0
    for p in cart:
        value = p.quantity * p.product.discounted_price
        amount = amount + value 
    totalamount = amount + 40

    return render(request,'app/addtocart.html',locals())

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Cart, Product  # Ensure Product is imported

def plus_cart(request):
    if request.method == 'GET':
        prod_id = request.GET.get('prod_id')

        # Fetch the Product instance
        product = get_object_or_404(Product, id=prod_id)

        # Get or create the cart entry
        cart_items = Cart.objects.filter(Q(product=product) & Q(user=request.user))

        if cart_items.exists():
            # Update the first item's quantity
            c = cart_items.first()
            c.quantity += 1
            c.save()
        else:
            # Create a new cart entry if it doesn't exist
            c = Cart.objects.create(product=product, user=request.user, quantity=1)

        # Calculate total amount and other details
        user = request.user
        cart = Cart.objects.filter(user=user)
        amount = sum(item.quantity * item.product.discounted_price for item in cart)
        totalamount = amount + 40  # Assuming shipping fee is 40

        data = {
            'quantity': c.quantity,
            'amount': amount,
            'totalamount': totalamount
        }

        return JsonResponse(data)

    if request.method == 'GET':
        prod_id = request.GET.get('prod_id')
        cart_items = Cart.objects.filter(Q(product=prod_id) & Q(user=request.user))

        if cart_items.exists():
            # Update the first item's quantity
            c = cart_items.first()
            c.quantity += 1
            c.save()
        else:
            # Create a new cart entry if it doesn't exist
            c = Cart.objects.create(product=prod_id, user=request.user, quantity=1)

        # Calculate total amount and other details
        user = request.user
        cart = Cart.objects.filter(user=user)
        amount = sum(item.quantity * item.product.discounted_price for item in cart)
        totalamount = amount + 20  # Assuming shipping fee is 40

        data = {
            'quantity': c.quantity,
            'amount': amount,
            'totalamount': totalamount
        }

        return JsonResponse(data)

def remove_cart(request):
    if request.method == 'GET':
        prod_id = request.GET['prod_id']
        c = Cart.objects.filter(Q(product=prod_id) & Q(user=request.user))
        c.delete()
        user=request.user
        cart = Cart.objects.filter(user=user)
        amount = 0
        for p in cart:
            value = p.quantity * p.product.discounted_price
            amount = amount + value 
        totalamount = amount + 40
        data={
            'amount':amount,
            'totalamount':totalamount
        }
        return JsonResponse(data)
    
def minus_cart(request):
 from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Cart, Product  # Ensure Product is imported

def minus_cart(request):
    if request.method == 'GET':
        prod_id = request.GET.get('prod_id')

        # Fetch the Product instance
        product = get_object_or_404(Product, id=prod_id)

        # Get the cart entry
        cart_items = Cart.objects.filter(Q(product=product) & Q(user=request.user))

        if cart_items.exists():
            c = cart_items.first()
            if c.quantity > 1:
                # Decrease the quantity by 1
                c.quantity -= 1
                c.save()  # Correct save method
            else:
                # Remove the cart item if quantity is 1
                c.delete()

            # Calculate total amount and other details
            user = request.user
            cart = Cart.objects.filter(user=user)
            amount = sum(item.quantity * item.product.discounted_price for item in cart)
            totalamount = amount + 40  # Assuming shipping fee is 40

            data = {
                'quantity': c.quantity if c.quantity > 0 else 0,
                'amount': amount,
                'totalamount': totalamount
            }

            return JsonResponse(data)

        else:
            # If the cart item does not exist
            return JsonResponse({'error': 'Item not found in cart'}, status=404)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

class checkout(View):
    def get(self, request):
        user = request.user
        add = Customer.objects.filter(user=user)
        cart_items = Cart.objects.filter(user=user)
        
        famount = 0
        for p in cart_items:
            value = p.quantity * p.product.discounted_price
            famount += value  # Calculate total amount for cart items

        totalamount = famount + 40  # Adding shipping fee
        
        # client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))
        
        # # Create order with the total amount in paise
        # data = {
        #     "amount": totalamount * 100,  # Convert to paise
        #     "currency": "INR",
        #     "receipt": "order_rcptid_12"  # Adjust as necessary
        # }
        
        # payment_response = client.order.create(data=data)
        # print(payment_response)

        # order_id = payment_response['id']
        # order_status = payment_response['status']
        # if order_status == 'created':
        #     payment = Payment(
        #         user=user,
        #         amount=totalamount,
        #         razorpay_order_id=order_id,
        #         razorpay_payment_status=order_status
        #     )
        #     payment.save()
        
        return render(request, "app/checkout.html", locals())
    
    def post(self, request):
        user = request.user
        customer_id = request.POST.get('custid')
        total_amount = request.POST.get('totamount')
        
        if not customer_id:
            messages.warning(request, "Please select a shipping address")
            return redirect("checkout")
        
        # Create a Payment record with temporary order ID
        payment = Payment(
            user=user,
            amount=total_amount,
            razorpay_order_id=f"temp_{user.id}_{int(float(total_amount))}",
            razorpay_payment_status="created"
        )
        payment.save()
        
        # Redirect to UPI payment page with customer ID
        return redirect(f'/upi-payment/?custid={customer_id}')

def upi_payment(request):
    user = request.user
    custid = request.GET.get('custid')
    
    if not custid:
        messages.warning(request, "Invalid request")
        return redirect("checkout")
    
    # Get cart items to calculate total
    cart_items = Cart.objects.filter(user=user)
    
    famount = 0
    for p in cart_items:
        value = p.quantity * p.product.discounted_price
        famount += value
    
    totalamount = famount + 40  # Adding shipping fee
    
    return render(request, "app/upi_payment.html", locals())

def payment_done(request):
    order_id=request.GET.get('order_id')
    payment_id=request.GET.get('payment_id')
    cust_id=request.GET.get('cust_id')
    user=request.user
    customer=Customer.objects.get(id=cust_id)
    
    # Find payment by user (if coming from UPI payment, order_id might be different)
    try:
        payment = Payment.objects.filter(user=user).latest('id')
        payment.razorpay_order_id = order_id
        payment.razorpay_payment_id = payment_id
        payment.paid = True
        payment.save()
    except Payment.DoesNotExist:
        messages.warning(request, "Payment information not found")
        return redirect("checkout")
    
    cart=Cart.objects.filter(user=user)
    for c in cart:
        OrderPlaced(user=user,customer=customer,product=c.product,quantity=c.quantity,payment=payment).save()
        c.delete()

    return redirect("orders")

def orders(request):
    if request.user.is_authenticated:
        # Get all orders placed by the current user
        orders = OrderPlaced.objects.filter(user=request.user).order_by('-ordered_date')
        return render(request, "app/orders.html", {'orders': orders})
    else:
        return redirect("login")

def delete_order(request, order_id):
    if request.user.is_authenticated:
        try:
            order = OrderPlaced.objects.get(id=order_id, user=request.user)
            order.delete()
            messages.success(request, "Order deleted successfully!")
        except OrderPlaced.DoesNotExist:
            messages.error(request, "Order not found!")
        return redirect("orders")
    else:
        return redirect("login")



         
      
        