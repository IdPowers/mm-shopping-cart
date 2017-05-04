import logging
from collections import defaultdict

from django.http import HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect
from django.utils import timezone
from django.core.urlresolvers import reverse_lazy
from django.views.generic import ListView, DeleteView

from tempitura import api
from tempitura.exceptions import APIError
from tickets.models import Ticket
from .models import CartItem


logger = logging.getLogger("private-project.{}".format(__name__))


class Cart(ListView):
    model = CartItem
    template_name = 'cart/cartitem_list.html'

    def get_context_data(self, **kwargs):
        context = super(Cart, self).get_context_data(**kwargs)

        fees = 0.0
        date_expiration = None

        tempitura_session_key = self.request.user.tempitura_session_key

        try:
            logger.debug("Check cart")
            result = api.get_cart(
                tempitura_session_key, cache=True, timeout=30)
            if result:
                fees = float(result['Order']['HandlingCharges'])
                date_expiration = api.get_ticket_expiration(
                    tempitura_session_key,
                    as_utc=True,
                    cache=True, timeout=30,
                )

                if date_expiration and date_expiration < timezone.now():
                    self.request.user.cart_items.remove_tickets()

            logger.debug("Cart items successfully received")

        except APIError:
            logger.debug("There are expired tickets")
            self.request.user.cart_items.remove_tickets()

        # Do not display expiration time if cart is empty
        if self.request.user.cart_items.count() == 0:
            date_expiration = 0

        context['sub_total'] = self.request.user.cart_items.total_cost()
        context['fees'] = fees
        context['total_cost'] = context['sub_total'] + fees
        context['date_expiration'] = date_expiration

        return context

    def get_queryset(self):
        return self.request.user.cart_items.order_by('id')


def clean(request):
    api.transfer_session(request.user)

    model_ids_map = defaultdict(list)
    for cart_item in request.user.cart_items.all():
        model = cart_item.content_type.model_class()
        model_ids_map[model].append(cart_item.object_id)

    for model, ids in model_ids_map.items():
        ids and model.objects.filter(id__in=ids).delete()

    request.user.cart_items.all().delete()

    return redirect('cart:cart')


class ItemDelete(DeleteView):
    def get(self, request, *args, **kwargs):
        return self.post(request)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=request.user.cart_items.all())
        success_url = self.get_success_url()
        self.object.delete(request.user.tempitura_session_key)
        return HttpResponseRedirect(success_url)

    model = CartItem
    success_url = reverse_lazy('cart:cart')
