from django.db import models

# TODO: move it somewhere
class ProductMixin(models.Model):
    def get_title(self):
        raise NotImplementedError

    def get_description(self):
        raise NotImplementedError

    def get_cost(self):
        raise NotImplementedError

    def add_to_cart_callback(self, *args, **kwargs):
        raise NotImplementedError

    def checkout_callback(self, *args, **kwargs):
        raise NotImplementedError

    def transfer_to_user(self, user, *args, **kwargs):
        raise NotImplementedError

    def delete_callback(self, tempitura_session_key, *args, **kwargs):
        raise NotImplementedError

    class Meta:
        abstract = True
