from django.urls import path,include
from . import views



urlpatterns=[
    path('signout', views.signout,name='signout'),
    path('',views.signup,name='signup'),
    path('signin',views.signin,name='signin'),
    path('email_varification', views.email_varification,name='email_varification'),
    path('otp_check', views.otp_check,name='otp_check'),
    path('forgot_password',views.forgot_password,name='forgot_password'),
    path('change-password', views.change_password, name='change_password'),
    path('admin_signin',views.admin_signin,name='admin_signin'),
    path('account_details', views.account_details,name='account_details'),
    path('old_password/<int:user_id>', views.old_password,name='old_password'),
    path('admin_forgot_password', views.admin_forgot_password,name='admin_forgot_password'),
    path('Admin_verify', views.Admin_verify,name='Admin_verify'),
    path('verify-referral-code/', views.verify_referral_code, name='verify_referral_code'),

]
