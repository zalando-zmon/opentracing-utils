from django.conf.urls import url

import app.views as views


urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^user', views.user, name='user'),
    url(r'^error', views.error, name='error'),
    url(r'^bad', views.bad_request, name='bad'),
    url(r'^nested', views.nested, name='nested'),
]
