from django.urls import path
from users import views, supabase_views

urlpatterns = [
    # REST-compatible client endpoints (new frontend)
    path('clients/', supabase_views.list_clients),
    path('clients/<str:client_id>/', supabase_views.update_client_detail),
    path('invite_client/', supabase_views.invite_client_handler),

    path('signup-user/', views.signup_user),
    path('check-auth/', supabase_views.check_auth),
    path('entitlements/summary/', supabase_views.entitlement_summary),
    path('invalidate-session/', supabase_views.invalidate_session),
    path('get-prefilled-data/', views.get_prefilled_data),
    path('onboard-client/', supabase_views.onboard_new_client),
    path('check-existing-user/', supabase_views.check_existing_user),
    path('onboard-existing-client/', supabase_views.onboard_existing_client),
    path('filter_with_details/', supabase_views.filter_cases_clients_with_details),
    path('get-courts/', views.get_courts),
    path('get-districts/', views.get_districts),
    path('get-states/', views.get_states),
    path('verify-barcode/', views.verify_barcode),
    path('verify-email/', views.verify_email),
    path('submit-feedback/', supabase_views.submit_feedback),
    path("auth/check-username", supabase_views.check_username),
    path("onboard/", supabase_views.onboarding_new_user),
    path("get-profile", supabase_views.get_profile),
    path("login-user/", supabase_views.supabase_login),
    path("send-reset-password-link/", supabase_views.send_reset_password_link),
    path("reset-user-password/", supabase_views.reset_password),
    path("sign-out-user/", supabase_views.sign_out_supabase),
    path("signup-onboarded-client/", supabase_views.profile_update_of_client_onboarded_by_lawyer),
    path('add_case_client', supabase_views.add_case_client),
]