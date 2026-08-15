from django.urls import path

from app.api.views import checkout_quote, create_payment

urlpatterns = [
    path("payments", create_payment, name="create-payment"),
    path("checkout/quote", checkout_quote, name="checkout-quote"),
]
