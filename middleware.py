# -*- coding: utf-8 -*-

from django.utils import timezone
from django.contrib.sessions.models import Session


class AnonymousCart(object):
    def process_request(self, request):
        """The middleware’s goal is to allow anonymous users refer to cart items
        similar as logged in user does

        """
        session_obj = Session.objects.get(
            session_key=request.session.session_key,
            expire_date__gt=timezone.now()
        )
        if request.user.is_authenticated():
            return

        # session will be removed when user log in, but we save anonymous
        # session key in order to find cart items that were associated with the
        # removed session
        request.session['anonymous_session_key'] = request.session.session_key

        session_obj = Session.objects.get(
            session_key=request.session.session_key,
            expire_date__gt=timezone.now()
        )

        # Anonymous user hasn't cart_items object (CartManager object), but
        # session_obj has. Create cart_items property for anonymous user object
        # with session_obj's cart items.
        request.user.cart_items = session_obj.cart_items
