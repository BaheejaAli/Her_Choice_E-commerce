from django.contrib import admin
from accounts.views.user_auth import google_callback_safe
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/", include("accounts.urls")),
    # path("accounts/google/login/callback/", google_callback_safe, name="google_callback"),
    # path("accounts/", include("allauth.socialaccount.providers.google.urls")),
    path("accounts/", include("allauth.urls")),

    path("admin-panel/", include("adminpanel.urls")),
    path("", include("user_section.urls")),
    path("", include("offer.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



