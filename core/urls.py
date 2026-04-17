from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('post-pet/', views.post_pet, name='post_pet'),
    path('lost-pets/', views.index, name='lost_pets'),
    path('sightings/', views.index, name='sightings'),
    path('rescues/', views.index, name='rescues'),
    path('adoptions/', views.index, name='adoptions'),
    path('report/<int:id>/', views.report_detail, name='report_detail'),
    path('resolve-report/<int:id>/', views.resolve_report, name='resolve_report'),
    path('claim-ownership/<int:id>/', views.claim_ownership, name='claim_ownership'),
    path('op-rescue/<int:id>/', views.op_rescue, name='op_rescue'),
    path('rescue-verification/<int:id>/', views.submit_rescue_verification, name='submit_rescue_verification'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('settings/', views.settings_view, name='settings'),
    path('fund/<int:fund_id>/', views.fund_detail, name='fund_detail'),
    path('report/<int:sighting_id>/request-fund/', views.create_fund_request, name='create_fund_request'),
    path('fund/<int:fund_id>/donate/', views.submit_donation, name='submit_donation'),
    path('verify-donation/<int:donation_id>/', views.verify_donation_payment, name='verify_donation_payment'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('api/notifications/<int:notif_id>/read/', views.api_mark_notif_read, name='api_mark_notif_read'),
    path('admin-panel/', views.custom_admin_dashboard, name='custom_admin_dashboard'),
    path('admin-panel/verify-claim/<int:claim_id>/', views.verify_claim, name='verify_claim'),
    path('admin-panel/verify-fund/<int:fund_id>/', views.verify_fund, name='verify_fund'),
    path('admin-panel/verify-rescue/<int:rescue_id>/', views.verify_rescue, name='verify_rescue'),
]
