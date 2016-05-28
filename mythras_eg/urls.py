from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin
from enemygen.reg_views import MyRegistrationView
from dajaxice.core import dajaxice_autodiscover

admin.autodiscover()
dajaxice_autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^dajaxice/', include('dajaxice.urls')),
    url(r'^accounts/register/$', MyRegistrationView.as_view(), name='registration_register'),
    url(r'^accounts/', include('registration.backends.simple.urls')),
    url(r'^', include('enemygen.urls')),
    #url(r'^mw_enemygen/', include('mw.urls')),
)

urlpatterns += staticfiles_urlpatterns() #For Dajaxice
