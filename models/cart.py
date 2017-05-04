import logging
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from model_utils.models import TimeStampedModel

from tempitura import api
from tempitura.utils import remove_expired_tickets
from accounts.models import AnonymousUser


logger = logging.getLogger("private-project.{}".format(__name__))


class CartManager(models.Manager):
    use_for_related_fields = True

    def __get_owner(self):
        # authenticated user
        if isinstance(self.instance, get_user_model()):
            return self.instance
        # anonymous user
        elif isinstance(self.instance, Session):
            return AnonymousUser(self.instance.session_key)
        else:
            raise Exception('Wrong owner object type')

    def get_queryset(self):
        """Returns unpaid items if instance is User"""
        filter_items = {}
        if hasattr(self, 'instance') and isinstance(self.instance, get_user_model()):
            filter_items['is_paid'] = False

        return super(CartManager, self).get_queryset().filter(**filter_items)

    def set_as_paid(self):
        """All unpaid items set as paid"""
        for item in self.get_queryset().prefetch_related('product'):
            item.product.checkout_callback()

        return self.get_queryset().update(is_paid=True)

    def new(self, product, **kwargs):
        """Add any item to the shopping cart

        Can't use `add` name, it used by RelatedManager
        here django/db/models/fields/related

        Args:
            product (object): model object based on ProductMixin model

        Returns:
            CartItem object

        """
        self.user = self.__get_owner()

        # associate cart item with user
        if isinstance(self.instance, get_user_model()):
            owner_object_data = {'user': self.instance}
        # associate cart item with session
        elif isinstance(self.instance, Session):
            owner_object_data = {
                'session': self.instance,
                'session_key': self.instance.session_key
            }

        tempitura_session_key = self.user.tempitura_session_key

        logger.debug("New cart item: tempitura key %s", tempitura_session_key)

        remove_expired_tickets(self.instance.cart_items, tempitura_session_key)

        try:
            product.add_to_cart_callback(tempitura_session_key, **kwargs)
        except api.TaskIsPending:
            # to prevent extra the same products in the
            # private-project shopping cart when we use celery
            product.delete()
            raise

        item = self.model(product=product, **owner_object_data)
        item.save()

        return item

    def transfer_to_user(self, session_key, user):
        """Transfer all cart items to user"""
        for cart_item in CartItem.objects.filter(session_key=session_key):
            cart_item.user = user
            cart_item.session = None
            cart_item.session_key = None
            cart_item.save()

            cart_item.product.transfer_to_user(user)

    def total_cost(self):
        """Total cost of all unpaid items

        Returns:
            float

        """
        cost = 0.0
        for item in self.get_queryset().prefetch_related('product'):
            if item.product:
                cost += item.product.get_cost()

        return cost

    def remove_tickets(self):
        from tickets.models import Ticket
        logger.debug("Remove all tickets")
        cart_item_qs = self.get_queryset().filter(
            content_type=ContentType.objects.get_for_model(Ticket)
        )

        ticket_ids = list(cart_item_qs.values_list('object_id', flat=True))
        ticket_qs = Ticket.objects.filter(id__in=ticket_ids)

        ticket_data_list = list(
            Ticket.objects.filter(
                id__in=ticket_ids
            ).values_list('performance__tempitura_no', 'li_seq_no')
        )

        user = self.__get_owner()
        try:
            api.bulk_release_tickets(
                user.tempitura_session_key,
                ticket_data_list
            )
        except api.APIError:
            # TODO: maybe we should call transfer session?
            logger.exception('Tickets remove error!')
        finally:
            ticket_qs.delete()
            cart_item_qs.delete()

    def get_types(self):
        """Return model names of products contains in the shopping cart"""
        # {'donation', 'packageproduct', 'ticket'}
        items = self.get_queryset()
        return tuple(set([item.product._meta.model_name for item in items]))

    def is_only_packages(self):
        """Is cart contains only packages or empty"""
        if self.get_queryset().count() == 0:
            return True

        return self.get_types() == ('packageproduct',)


class CartItem(TimeStampedModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    product = GenericForeignKey()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="cart_items",
        null=True,
        blank=True
    )

    # this field will be necessary for using cart_manager from Session object
    session = models.ForeignKey(
        Session,
        related_name="cart_items",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    # session object will be removed when user log in, because of that we should
    # save session key explicitly.
    session_key = models.CharField(max_length=255, null=True, blank=True)
    is_paid = models.BooleanField(default=False)

    cart_manager = CartManager()
    objects = models.Manager()

    def delete(self, tempitura_session_key, *args, **kwargs):
        self.product.delete_callback(tempitura_session_key)
        self.product.delete()
        super(CartItem, self).delete(*args, **kwargs)

    def clean(self):
        if not self.user and not self.session_key:
            raise ValidationError("User or Session key should be filled")

    def __str__(self):
        if not self.product:
            return "Removed item"

        return self.product.get_title()
