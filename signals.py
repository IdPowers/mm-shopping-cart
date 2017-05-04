from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models.cart import CartItem


@receiver(user_logged_in)
def move_cart_items_to_logged_in_user(sender, user, request, **kwargs):
    """The callback's goal is to change cart items owner from anonymous session
    to logged in user

    """
    if not request.session.get('anonymous_session_key'):
        return

    CartItem.cart_manager.transfer_to_user(
        request.session.get('anonymous_session_key'), user)

    del request.session['anonymous_session_key']
