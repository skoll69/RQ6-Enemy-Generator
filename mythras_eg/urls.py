from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin
from django.contrib.auth import views as auth_views
from enemygen.reg_views import MyRegistrationView
from dajaxice.core import dajaxice_autodiscover

admin.autodiscover()
dajaxice_autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^dajaxice/', include('dajaxice.urls')),
    url(r'^accounts/register/$', MyRegistrationView.as_view(), name='registration_register'),

      url(r'^accounts/password/reset/$',
                    auth_views.password_reset,
                    name='password_reset'),
      url(r'^accounts/password/reset/done/$',
                    auth_views.password_reset_done,
                    name='password_reset_done'),
      url(r'^accounts/password/reset/complete/$',
                    auth_views.password_reset_complete,
                    name='password_reset_complete'),
      url(r'^accounts/password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
                    auth_views.password_reset_confirm,
                    name='password_reset_confirm'),


    url(r'^accounts/', include('registration.backends.simple.urls')),
    url(r'^', include('enemygen.urls')),
    #url(r'^mw_enemygen/', include('mw.urls')),
)

urlpatterns += staticfiles_urlpatterns() #For Dajaxice
