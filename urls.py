from django.conf.urls import patterns, url

from .views import Cart, ItemDelete, clean

urlpatterns = patterns('cart.views',
    url(r'^$', Cart.as_view(), name='cart'),
    url(r'^delete/(?P<pk>\d+)/$', ItemDelete.as_view(), name='delete'),
    url(r'^clean/$', clean),
)
