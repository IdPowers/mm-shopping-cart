"""Each user object has `cart_items` property.

request.user.cart_items.all(): returns unpaid items
request.user.cart_items.new(product_object)
request.user.cart_items.total_cost()
request.user.cart_items.delete(product_id)
request.user.cart_items.set_as_paid(): all products set as paid

"""
import signals
