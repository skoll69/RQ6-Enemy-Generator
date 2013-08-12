from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.simple import redirect_to

from django.contrib import admin
from registration import views as regviews

admin.autodiscover()

from dajaxice.core import dajaxice_autodiscover, dajaxice_config
dajaxice_autodiscover()

urlpatterns = patterns('',
    url(r'^$', redirect_to, {'url': 'enemygen/'}),
    url(r'^enemygen/', include('enemygen.urls')),
    url(r'^admin/', include(admin.site.urls)),
    #url(dajaxice_config.dajaxice_url, include('dajaxice.urls')),
    url(r'^dajaxice/', include('dajaxice.urls')),
    url(r'^accounts/register/$',regviews.register, {'backend': 'registration.backends.simple.SimpleBackend', 'success_url': '/rq_tools/enemygen/'}, name='registration.views.register'),
    url(r'^accounts/', include('registration.backends.simple.urls')),
)

urlpatterns += staticfiles_urlpatterns() #For Dajaxice