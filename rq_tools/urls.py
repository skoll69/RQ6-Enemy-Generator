from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
#from django.views.generic.simple import redirect_to

from django.contrib import admin
from registration import views as regviews

from enemygen.reg_views import MyRegistrationView

admin.autodiscover()

from dajaxice.core import dajaxice_autodiscover, dajaxice_config
dajaxice_autodiscover()

urlpatterns = patterns('',
    url(r'^enemygen/', include('enemygen.urls')),
    url(r'^admin/', include(admin.site.urls)),
    #url(dajaxice_config.dajaxice_url, include('dajaxice.urls')),
    url(r'^dajaxice/', include('dajaxice.urls')),
    url(r'^accounts/register/$', MyRegistrationView.as_view(), name='registration_register'),
    url(r'^accounts/', include('registration.backends.simple.urls')),
)

urlpatterns += staticfiles_urlpatterns() #For Dajaxice
