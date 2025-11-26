
from django.shortcuts import render,redirect
from django.contrib import messages
from django.views.decorators.cache import never_cache
from Home.views import home
from Users.models import Custom_User as User
from django.contrib.auth import login as authlogin,logout,authenticate
import pyotp
from admin_panel.views import admin_panel
from django.contrib.auth.decorators import login_required,user_passes_test
from .forms import varification
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime,timedelta
from Users.models import Address,Profile,Wallet



# Create your views here.
OTP_VALIDITY_PERIOD = 1
secret_key = pyotp.random_base32()

@never_cache
def signin(request):
    if request.user.is_authenticated:
        return redirect(home)
    if request.method == 'POST' :
        username= request.POST['username']
        if not User.objects.filter(username=username):
            messages.error(request,'Ther is no user name like this')
            return redirect(signin)
        account = User.objects.get(username=username)
        if account.is_active:
            pass
        else:
            messages.error(request,'This account is temporary blocked')
            return redirect(signin)
        password=request.POST['password']
        user=authenticate(username=username, password=password)
        if user:
            authlogin(request,user)
            return redirect(home)
        else :
            messages.error(request,'Please check the username and password')
            return redirect(signin)
    return render(request,'signin.html')




def signout(request):
    if request.session.session_key:
        user_id = request.session.get("_auth_user_id")
        user = User.objects.get(pk=user_id)
        if user.is_staff:
            logout(request)
            return redirect(admin_signin)
        
        else:  
            logout(request)
            return redirect(home)


@never_cache

def signup(request):
    if request.user.is_authenticated:
        return redirect(home)
    
    user=None
    error_message=None
    if request.method=='POST':
        try:
            username = request.POST['username']
            email = request.POST['email']
            # check if username or email already exists
            if User.objects.filter(username=username).exists():
                messages.error(request, "This username is already taken. Please choose another one.")

                
                return render(request, 'SignUp.html')

            if User.objects.filter(email=email).exists():
                messages.error(request, "This email is already registered. Please use another email.")
                return render(request, 'SignUp.html')


            request.session['username']=request.POST['username']
            request.session['password']=request.POST['password']
            request.session['email']=request.POST['email']
            request.session['f_name']=request.POST['f_name']
            request.session['l_name']=request.POST['l_name']
            request.session['phone']=request.POST['phone']
            request.session['type'] = 'notexisting'
            
            return render(request,'Confirm_email.html',{'email':email})
        except Exception as e:
            messages.error(request,"this username or email address is already taken .please choose another one.")
            return redirect(signup)
    return render(request,'SignUp.html',{'user':user})  
@never_cache
def email_varification(request):
    form = varification()
    if request.method == 'POST':
        form = varification(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            username = form.cleaned_data.get('username')
            request.session['email'] = email
            if username:
                request.session['username'] = username

            # Case 1: Signup flow (type = notexisting)
            if request.session.get('type') == 'notexisting':
                if User.objects.filter(email=email).exists():
                    messages.error(request, "This email is already registered. Please sign in.")
                    return redirect('signin')

                if User.objects.filter(username=username).exists():
                    messages.error(request, "This username is already taken. Please sign in.")
                    return redirect('signin')

            # Case 2: Forgot password flow (type = exist)
            elif request.session.get('type') == 'exist':
                if not User.objects.filter(email=email).exists():
                    messages.error(request, "This email is not registered with Lapcon.")
                    return redirect('forgot_password')
                

            elif request.session.get == 'change_email':
                if User.objects.filter(email=email).exists():
                    messages.error(request, "This email is already in use by another account.")
                    return redirect('account_details')
                request.session['new_email'] = email     

            # ✅ Send OTP
            secret_key = pyotp.random_base32()
            request.session['secret_key'] = secret_key
            totp = pyotp.TOTP(secret_key)
            otp = totp.now()
            request.session['otp'] = otp
            request.session['otp_created_at'] = datetime.now().timestamp()

            subject = "Email verification - Lapcon"
            message = f"Your OTP is ({otp}). Use this OTP to verify your email. Please do not share it with anyone."
            send_mail(subject, message, settings.EMAIL_HOST_USER, [email], fail_silently=False)

            return redirect('otp_check')

    return render(request, 'confirm_email.html', {'form': form})

@never_cache
def otp_check(request):
    if request.method == 'POST':
        if 'resend_otp' in request.POST:
            # resend otp logic
            totp = pyotp.TOTP(secret_key)
            otp = totp.now()
            request.session['otp'] = otp
            request.session['otp_created_at'] = datetime.now().timestamp()

            subject = 'Resend OTP - Lapcon'
            message = f"Your new OTP is ({otp}). Use this to verify your email. Please do not share this OTP with anyone."
            recipient = request.session['email']
            send_mail(subject, message, settings.EMAIL_HOST_USER, [recipient], fail_silently=False)

            messages.success(request, 'A new OTP has been sent to your email.')
            return redirect(otp_check)

        #  combine OTP from multiple inputs
        otp_c = "".join(request.POST.getlist("otp[]"))
        otp = str(request.session.get('otp'))
        otp_created_at = datetime.fromtimestamp(
            request.session.get('otp_created_at', datetime.now().timestamp())
        )

        # check if otp still valid
        if datetime.now() > otp_created_at + timedelta(minutes=OTP_VALIDITY_PERIOD):
            messages.error(request, 'The OTP has expired. Please request a new one.')
            return redirect(otp_check)

        if otp_c == otp:
            email = request.session['email']
            flow_type = request.session.get('type')

            if flow_type == 'exist':
                
                return redirect(change_password)
            if flow_type=='notexisting':
              if not User.objects.filter(email=email).exists():  
                username = request.session.get('username')
                if not username:  # fallback if session failed
                         username = email.split("@")[0] 
                         
                          
                password = request.session.get('password')
                phone = request.session.get('phone')
                f_name = request.session.get('f_name')
                l_name = request.session.get('l_name')
                referral_code = request.session.get('valid_referral_code')

                user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=f_name,
                last_name=l_name,
                phone=phone
                )
                
                user.save()
                messages.success(request, 'Account created successfully! Please log in.')


            if flow_type == 'change_email':
                new_email = request.session.get('new_email')
                if new_email:
                    user = request.user
                    user.email = new_email
                    user.save()
                    messages.success(request, 'Your email has been updated successfully!')

            request.session.flush()
            return redirect(signin)
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            return redirect(otp_check)

    otp_created_at = datetime.fromtimestamp(
        request.session.get('otp_created_at', datetime.now().timestamp())
    )
    time_left = max(0, int((otp_created_at + timedelta(minutes=OTP_VALIDITY_PERIOD) - datetime.now()).total_seconds()))
    return render(request, 'verifyemail.html', {'time_left': time_left})

# def forgot_password(request):
#     request.session['type']='exist'
#     return render(request,'Confirm_email.html')  

@never_cache
def forgot_password(request):
    """Step 1: User enters their email for password reset"""
    request.session['type'] = 'exist'   # tells flow this is reset
    form = varification()

    if request.method == 'POST':
        form = varification(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            if not User.objects.filter(email=email).exists():
                messages.error(request, "This email is not registered with us.")
                return redirect('forgot_password')

            request.session['email'] = email

            # Send OTP
            totp = pyotp.TOTP(secret_key)
            otp = totp.now()
            request.session['otp'] = otp
            request.session['otp_created_at'] = datetime.now().timestamp()

            subject = "Password Reset OTP - Lapcon"
            message = f"Your OTP is ({otp}). Use this OTP to reset your password. Do not share it with anyone."
            send_mail(subject, message, settings.EMAIL_HOST_USER, [email], fail_silently=False)

            messages.success(request, "An OTP has been sent to your email.")
            return redirect('otp_check')   

    return render(request, 'confirm_email.html', {'form': form})


def change_password(request):
    """Step 2: After OTP verified, user sets new password"""
    if request.method == 'POST':
        email = request.session.get('email')
        if not email:
            messages.error(request, "Session expired. Please try again.")
            return redirect('forgot_password')

        user = User.objects.get(email=email)
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('change_password')

        user.set_password(password)
        user.save()

        logout(request)
        request.session.pop('email', None)
        
        messages.success(request, "Password changed successfully! Please sign in.")
        return redirect(signin)

    return render(request, 'change_password.html')


def old_password(request, user_id):
   
    if request.method == 'POST':
        password = request.POST.get('password')
        username = User.objects.get(pk=user_id).username
        user_p = authenticate(username=username, password=password)

        if user_p:
            request.session['email'] = user_p.email
            return redirect('change_password')
        else:
            messages.error(request, "Old password is incorrect.")

    return render(request, 'old_password.html')


#Admin account
@never_cache
def admin_signin(request):
    if request.user.is_authenticated:  
        if request.user.is_staff:  #  check staff 
            return redirect(admin_panel)
        else:
            return redirect(home)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password'] 
        user = authenticate(username=username, password=password) 
        if user and user.is_staff:  # only allow staff
            authlogin(request, user) 
            return redirect(admin_panel)
        else:
            messages.error(request, 'Please check username and password')
            return redirect(admin_signin)

    return render(request, 'admin/adminsignin.html')   

def admin_forgot_password(request):
    form = varification()
    if request.method == 'POST':
        if not User.objects.filter(email=request.POST['email']).exists():
            messages.error(request, 'This mail id do not have an account in Lapcon')
            return redirect(admin_forgot_password)
        user = User.objects.get(email=request.POST['email'])
        if user.is_staff:
            form = varification(request.POST)
            if form.is_valid():
                print('hi')
                request.session['email'] = request.POST['email']
                subject = 'Email varification Lapcon'
                totp = pyotp.TOTP(secret_key)
                otp = totp.now()
                request.session['otp'] = otp
                message = f'Your otp is ({otp}).Use this otp to verify your email id to change your passsword for admin account in Lapcon'
                recipient = form.cleaned_data.get('email')
                send_mail(subject, message, settings.EMAIL_HOST_USER, [recipient], fail_silently=False)
                return redirect(Admin_verify)
        else :
            messages.error(request,'This mail id do not the admin')
            return redirect(admin_forgot_password)
    return render(request,'admin/forgetpassword.html')


def admin_change_password(request):
    if request.method == 'POST' :
        email = request.session['email']
        user = User.objects.get(email=email)
        user.set_password(request.POST['password']) 
        user.save()
        request.session.flush()
        messages.success(request,'Password was changed sussesfuly')
        return redirect(admin_signin)
    return render(request,'admin/change_password.html')



@never_cache
def Admin_verify(request):
    if request.method == 'POST':
        if 'resend_otp' in request.POST:
            # Resend OTP logic
            totp = pyotp.TOTP(secret_key)
            otp = totp.now()
            request.session['otp'] = otp
            request.session['otp_created_at'] = datetime.now().timestamp()

            # Resend the email
            subject = 'Resend OTP - Lapcon'
            message = f'Your new OTP is ({otp}). Use this to verify your email. Please do not share this OTP with anyone.'
            recipient = request.session['email']
            send_mail(subject, message, settings.EMAIL_HOST_USER, [recipient], fail_silently=False)

            messages.success(request, 'A new OTP has been sent to your email.')
            return redirect(Admin_verify)

        otp_c = request.POST['otp']
        otp = request.session.get('otp')
        otp_created_at = datetime.fromtimestamp(request.session.get('otp_created_at', datetime.now().timestamp()))
        
        # Check if OTP is still valid
        if datetime.now() > otp_created_at + timedelta(minutes=OTP_VALIDITY_PERIOD):
            messages.error(request, 'The OTP has expired. Please request a new one.')
            return redirect(Admin_verify)
        
        if int(otp) == int(otp_c):
            email = request.session['email']
            return redirect(admin_change_password)
            
        else:
            messages.error(request, 'The OTPs do not match.')
            return redirect(Admin_verify)
    otp_created_at = datetime.fromtimestamp(request.session.get('otp_created_at', datetime.now().timestamp()))
    time_left = max(0, (otp_created_at + timedelta(minutes=OTP_VALIDITY_PERIOD) - datetime.now()).seconds)
    return render(request, 'admin/verify_otp.html', {'time_left': time_left}) 

@never_cache
def account_details(request):
    if request.user.is_authenticated:
        user = User.objects.get(username=request.user)
        addresses = Address.objects.filter(user=user)

        if request.method == 'POST':
            username = request.POST['username']
            email = request.POST['email']
            f_name = request.POST['f_name']
            l_name = request.POST['l_name']
            phone = request.POST['phone']
            new_email = request.POST.get('email') 
            # check if username is changing
            if user.username != username:
                if User.objects.filter(username=username).exists():
                    messages.error(request, 'This username is already taken')
                else:
                    user.username = username 

            # check if email is changing
            if new_email and user.email != new_email:
                if User.objects.filter(email=new_email).exists():
                    messages.error(request, "This email is already in use by another account.")
                    return redirect('account_details')

                # store in session and redirect to email verification
                request.session['type'] = 'change_email'
                request.session['new_email'] = new_email
                return redirect('email_varification')  # go to OTP verification


            user.first_name = f_name
            user.last_name = l_name
            user.phone = phone
            user.save()

            messages.success(request, "Profile updated successfully!")

        profile, created = Profile.objects.get_or_create(user=user)
        return render(request, 'usesr_details.html', {
            'user': user,
            'addresses': addresses,
            'profile': profile
        })
    else:
        return redirect(signin)

    
def old_password(request, user_id):
    if request.method == 'POST' :
        password = request.POST['password']
        username = User.objects.get(pk=user_id).username
        user_P=authenticate(username=username ,password=password)
        
        if user_P:
            request.session['email'] = user_P.email
            return redirect(change_password)
        else :
            messages.error(request,'The old password was wrong')
            return redirect(old_password,user_id)
        
    return render(request,'old_password.html') 
























