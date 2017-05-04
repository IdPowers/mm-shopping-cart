import random
import logging

from django.contrib.auth import get_user_model, login
from django.core.urlresolvers import reverse_lazy
from django.test import TestCase
from django.test import Client

from mock import MagicMock

from localsite.models import Country, Locale
from vouchers.models import Voucher

logger = logging.getLogger("private-project.{}".format(__name__))
accout_model = get_user_model()


class TestCart(TestCase):
    def setUp(self):
        self.client = Client()

        self.user_login = 'test'
        self.user_password = 'password'
        self.user = get_user_model().objects.create_user(
            self.user_login,
            self.user_password
        )

        country = Country(**{
            'name': 'a', 'order': 1, 'code': 'a', 'tempitura_id': 4
        })
        country.save()

        Locale(**{
            'name': 'a',
            'order': 1,
            'tempitura_id': 9,
            'country': country,
            'code': 'a'
        }).save()

    def test_cart_logged_in(self):
        response = self.client.get('/')

        username = '%d@test.com' % random.randint(100000, 999999)
        password = '123456'
        response = self.client.post(reverse_lazy('signup'), {
            'email': username,
            'password1': password,
            'password2': password,
            'prefix': 'Dr',
            'firstname': 'Firstname',
            'middlename': 'Middlename',
            'lastname': 'Lastname',
            'suffix': 'AM',
            'phone_number': '123',
            'address1': 'Address1',
            'address2': 'Address2',
            'country': Country.objects.last().id,
            'state': Locale.objects.last().id,
            'city': 'City',
            'postal_code': '123',
        })

        # after successful registration user must be redirected
        self.assertEqual(response.status_code, 302)

        response = self.client.get('/')
        self.assertTrue(response.context['user'].is_authenticated())

        user = response.context['user']

        self.assertEqual(user.cart_items.count(), 0)

        # fill the cart
        product = Voucher(amount=1)
        product.save()
        user.cart_items.new(product)
        self.assertEqual(user.cart_items.count(), 1)

        product = Voucher(amount=2)
        product.save()
        user.cart_items.new(product)
        self.assertEqual(user.cart_items.count(), 2)

        # check if add_to_cart_callback method was called
        Voucher.add_to_cart_callback = MagicMock(return_value=True)
        product = Voucher(amount=3)
        product.save()
        self.assertFalse(Voucher.add_to_cart_callback.called)
        user.cart_items.new(product)
        self.assertTrue(Voucher.add_to_cart_callback.called)

    def test_cart_anon(self):
        response = self.client.get('/')

        self.assertFalse(response.context['user'].is_authenticated())

        user = response.context['user']

        self.assertEqual(user.cart_items.count(), 0)

        # fill the cart
        product = Voucher(amount=1)
        product.save()
        user.cart_items.new(product)
        self.assertEqual(user.cart_items.count(), 1)

        product = Voucher(amount=2)
        product.save()
        user.cart_items.new(product)
        self.assertEqual(user.cart_items.count(), 2)

        # check if add_to_cart_callback method was called
        Voucher.add_to_cart_callback = MagicMock(return_value=True)
        product = Voucher(amount=3)
        product.save()
        self.assertFalse(Voucher.add_to_cart_callback.called)
        user.cart_items.new(product)
        self.assertTrue(Voucher.add_to_cart_callback.called)

    def test_move_cart_from_anon_to_logged_in(self):
        response = self.client.get('/')

        username = '%d@test.com' % random.randint(100000, 999999)
        password = '123456'
        response = self.client.post(reverse_lazy('signup'), {
            'email': username,
            'password1': password,
            'password2': password,
            'prefix': 'Dr',
            'firstname': 'Firstname',
            'middlename': 'Middlename',
            'lastname': 'Lastname',
            'suffix': 'AM',
            'phone_number': '123',
            'address1': 'Address1',
            'address2': 'Address2',
            'country': Country.objects.last().id,
            'state': Locale.objects.last().id,
            'city': 'City',
            'postal_code': '123',
        })

        # after successful registration user must be redirected
        self.assertEqual(response.status_code, 302)

        # new client
        self.client = Client()
        response = self.client.get('/')
        self.assertFalse(response.context['user'].is_authenticated())
        user = response.context['user']

        self.assertEqual(user.cart_items.count(), 0)

        # Fill the cart
        product = Voucher(amount=1)
        product.save()
        user.cart_items.new(product)
        self.assertEqual(user.cart_items.count(), 1)

        product = Voucher(amount=2)
        product.save()
        user.cart_items.new(product)
        self.assertEqual(user.cart_items.count(), 2)

        # cart item must be related with session key not with user
        cart_item = user.cart_items.first()
        self.assertFalse(cart_item.user)
        self.assertTrue(cart_item.session_key)

        # log in
        auth_response = self.client.post(reverse_lazy('login'), {
            'username': username,
            'password': password
        })

        response = self.client.get('/')
        user = response.context['user']

        # after successful authorization user must be redirected
        self.assertEqual(auth_response.status_code, 302)

        # count of cart items must be the same as anonymous user
        self.assertTrue(user.is_authenticated())
        self.assertEqual(user.cart_items.count(), 2)

        # cart item must be related with user not with session key
        cart_item = user.cart_items.first()
        self.assertTrue(cart_item.user)
        self.assertFalse(cart_item.session_key)

    def test_remove_item(self):
        response = self.client.get('/')
        self.assertFalse(response.context['user'].is_authenticated())
        user = response.context['user']
        self.assertEqual(user.cart_items.count(), 0)

        Voucher.delete_callback = MagicMock(return_value=True)
        # fill the cart
        product = Voucher(amount=1)
        product.save()
        user.cart_items.new(product)
        self.assertEqual(user.cart_items.count(), 1)

        self.assertFalse(Voucher.delete_callback.called)
        user.cart_items.first().delete(user.tempitura_session_key)
        self.assertEqual(user.cart_items.count(), 0)
        self.assertTrue(Voucher.delete_callback.called)
