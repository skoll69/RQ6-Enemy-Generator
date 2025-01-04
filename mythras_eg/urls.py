import os

from django.conf.urls import include
from django.urls import re_path as url
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from enemygen.reg_views import MyRegistrationView

admin.autodiscover()

temp_path = static('/temp/', document_root=os.path.join(settings.PROJECT_ROOT, 'temp')) if settings.DEBUG else []
urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^accounts/register/$', MyRegistrationView.as_view(), name='registration_register'),

      url(r'^accounts/password/reset/$', auth_views.PasswordResetView.as_view(), name='password_reset'),
      url(r'^accounts/password/reset/done/$', auth_views.PasswordChangeDoneView.as_view(), name='password_reset_done'),
      url(r'^accounts/password/reset/complete/$', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
      url(r'^accounts/password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
                    auth_views.PasswordResetConfirmView.as_view(),
                    name='password_reset_confirm'),


    url(r'^accounts/', include('django_registration.backends.activation.urls')),
    url(r'^accounts/', include('django.contrib.auth.urls')),
    url(r'^', include('enemygen.urls')),
] + temp_path
