from django.urls import path
from core.apps.payments.api import CreatePaymentView, payment_webhook, TariffListView

urlpatterns = [
    path('create-payment/', CreatePaymentView.as_view(), name='create_payment'),
    path('payment-webhook/', payment_webhook, name='payment_webhook'),
    path('tariffs/', TariffListView.as_view(), name='tariff_list'),
]
