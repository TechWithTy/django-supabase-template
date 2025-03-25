from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from ._views import auth_view, client_view, database_view, edge_functions_view, realtime_view, storage_view

router = DefaultRouter()
router.register(r'users', views.UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    
    # Auth endpoints
    path('auth/anonymous/', auth_view.create_anonymous_user, name='create_anonymous_user'),
    path('auth/signin/email/', auth_view.sign_in_with_email, name='sign_in_with_email'),
    path('auth/signin/token/', auth_view.sign_in_with_id_token, name='sign_in_with_id_token'),
    path('auth/signin/otp/', auth_view.sign_in_with_otp, name='sign_in_with_otp'),
    path('auth/verify/otp/', auth_view.verify_otp, name='verify_otp'),
    path('auth/signin/oauth/', auth_view.sign_in_with_oauth, name='sign_in_with_oauth'),
    path('auth/signin/sso/', auth_view.sign_in_with_sso, name='sign_in_with_sso'),
    path('auth/signout/', auth_view.sign_out, name='sign_out'),
    path('auth/reset-password/', auth_view.reset_password, name='reset_password'),
    path('auth/session/', auth_view.get_session, name='get_session'),
    path('auth/session/refresh/', auth_view.refresh_session, name='refresh_session'),
    path('auth/user/<str:user_id>/', auth_view.get_user, name='get_user'),
    path('auth/user/<str:user_id>/update/', auth_view.update_user, name='update_user'),
    path('auth/user/<str:user_id>/identities/', auth_view.get_user_identities, name='get_user_identities'),
    path('auth/identity/link/', auth_view.link_identity, name='link_identity'),
    path('auth/identity/unlink/', auth_view.unlink_identity, name='unlink_identity'),
    path('auth/session/data/', auth_view.set_session_data, name='set_session_data'),
    path('auth/mfa/enroll/', auth_view.enroll_mfa_factor, name='enroll_mfa_factor'),
    path('auth/mfa/challenge/', auth_view.create_mfa_challenge, name='create_mfa_challenge'),
    path('auth/mfa/verify/', auth_view.verify_mfa_challenge, name='verify_mfa_challenge'),
    path('auth/mfa/unenroll/', auth_view.unenroll_mfa_factor, name='unenroll_mfa_factor'),
    path('auth/users/', auth_view.list_users, name='list_users'),
    
    # Database endpoints
    path('db/fetch/', database_view.fetch_data, name='fetch_data'),
    path('db/insert/', database_view.insert_data, name='insert_data'),
    path('db/update/', database_view.update_data, name='update_data'),
    path('db/upsert/', database_view.upsert_data, name='upsert_data'),
    path('db/delete/', database_view.delete_data, name='delete_data'),
    path('db/function/', database_view.call_function, name='call_function'),
    
    # Edge Functions endpoints
    path('edge/invoke/', edge_functions_view.invoke_function, name='invoke_edge_function'),
    path('edge/list/', edge_functions_view.list_functions, name='list_edge_functions'),
    
    # Realtime endpoints
    path('realtime/subscribe/', realtime_view.subscribe_to_channel, name='subscribe_to_channel'),
    path('realtime/unsubscribe/', realtime_view.unsubscribe_from_channel, name='unsubscribe_from_channel'),
    path('realtime/unsubscribe-all/', realtime_view.unsubscribe_all, name='unsubscribe_all'),
    path('realtime/channels/', realtime_view.get_channels, name='get_channels'),
    path('realtime/broadcast/', realtime_view.broadcast_message, name='broadcast_message'),
    
    # Storage endpoints
    path('storage/bucket/create/', storage_view.create_bucket, name='create_storage_bucket'),
    path('storage/bucket/', storage_view.get_bucket, name='get_storage_bucket'),
    path('storage/buckets/', storage_view.list_buckets, name='list_storage_buckets'),
    path('storage/bucket/update/', storage_view.update_bucket, name='update_storage_bucket'),
    path('storage/bucket/delete/', storage_view.delete_bucket, name='delete_storage_bucket'),
    path('storage/bucket/empty/', storage_view.empty_bucket, name='empty_storage_bucket'),
    path('storage/file/upload/', storage_view.upload_file, name='upload_storage_file'),
    path('storage/file/download/', storage_view.download_file, name='download_storage_file'),
    path('storage/files/', storage_view.list_files, name='list_storage_files'),
    path('storage/file/move/', storage_view.move_file, name='move_storage_file'),
    path('storage/file/copy/', storage_view.copy_file, name='copy_storage_file'),
    path('storage/file/delete/', storage_view.delete_file, name='delete_storage_file'),
    path('storage/url/signed/', storage_view.create_signed_url, name='create_signed_url'),
    path('storage/urls/signed/', storage_view.create_signed_urls, name='create_signed_urls'),
    path('storage/url/upload/', storage_view.create_signed_upload_url, name='create_signed_upload_url'),
    path('storage/url/upload/file/', storage_view.upload_to_signed_url, name='upload_to_signed_url'),
    path('storage/url/public/', storage_view.get_public_url, name='get_public_url'),
    
    # Client endpoints
    # Database
    path('client/db/query/', client_view.execute_query, name='execute_query'),
    
    # Storage
    path('client/storage/buckets/', client_view.list_buckets, name='list_buckets'),
    path('client/storage/bucket/create/', client_view.create_bucket, name='create_bucket'),
    path('client/storage/objects/', client_view.list_objects, name='list_objects'),
    path('client/storage/upload/', client_view.upload_file, name='upload_file'),
    path('client/storage/delete/', client_view.delete_file, name='delete_file'),
    
    # Edge Functions
    path('client/edge/invoke/', client_view.invoke_edge_function, name='client_invoke_edge_function'),
    
    # Realtime
    path('client/realtime/subscribe/', client_view.subscribe_to_channel, name='client_subscribe_to_channel'),
]
