import logging

from django.db import transaction
from django.db.models import F, Prefetch
from django.shortcuts import render, redirect
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from core.base_view import MultiplePaginationViewMixin
from core.choice_field_types import SubscriptionInvoiceStatusChoices
from core.pagination import CustomPaginator, MultiplePaginationMixin
from services.filters import SubscriptionFilter, SubscriptionInvoiceFilter
from services.models import (
    SubscriptionInvoice,
    Subscription
)
from services.serializers import (
    InvoiceReadOnlySerializer,
    IPGVerifyInvoiceSerializer,
    SubscriptionReadOnlySerializer,
)

logger = logging.getLogger(__name__)


class PaymentGatewayRedirectAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        # redirect the client to the appropriate payment page
        invoice: SubscriptionInvoice = get_object_or_404(
            SubscriptionInvoice.objects.all(),
            ipg_track_id=request.query_params.get("ipg_track_id")
        )
        return redirect(invoice.additional_data["payment_url"])


class SubscriptionInvoiceIPGVerifyAPIView(APIView):  # Only supports zibal for now

    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        data = dict(
            ipg_track_id=request.query_params.get('trackId')
        )

        # Verify with payment gateway
        serializer = IPGVerifyInvoiceSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        invoice: SubscriptionInvoice = serializer.save()

        context = dict(
            payment_successful=invoice.status == SubscriptionInvoiceStatusChoices.SUCCESSFUL,
            reference_id=invoice.reference_id,
            amount=int(invoice.amount / 10),
            client_redirect_url=invoice.additional_data["client_redirect_url"],
        )
        # redirect the client to the payment result html page directly
        return render(request, template_name="payment.html", context=context)

    def post(self, request, *args, **kwargs):
        data = dict(
            ipg_track_id=request.data.get('data').get('tracking_id'),
            crypto_gateway=True,
            status=request.data.get('data').get('status'),
        )
        serializer = IPGVerifyInvoiceSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        invoice: SubscriptionInvoice = serializer.save()
        return Response(dict(
            ok=True,
        ))


class SubscriptionViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    GenericViewSet,
    MultiplePaginationViewMixin
):
    serializer_class = SubscriptionReadOnlySerializer
    pagination_class = MultiplePaginationMixin
    filter_class = SubscriptionFilter

    def get_queryset(self):
        
        return Subscription.objects.select_related(
            "subscriber",
        ).prefetch_related(
            Prefetch(
                "invoices", SubscriptionInvoice.objects.filter(
                    status=SubscriptionInvoiceStatusChoices.SUCCESSFUL
                ),
                to_attr="successful_invoice"
            )
        ).annotate(
            # annotate the service title and type on the queryset for
            # direct access
            service_title=F("service__title"),
            service_type=F("service__service_type")
        ).filter(
            subscriber__owner_id=self.request.user.owner_id,
            is_paid=True
        ).order_by("-updated_at")


class SubscriptionInvoiceViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    GenericViewSet,
    MultiplePaginationViewMixin
):
    serializer_class = InvoiceReadOnlySerializer
    pagination_class = MultiplePaginationMixin
    filter_class = SubscriptionInvoiceFilter

    def get_queryset(self):
        
        return SubscriptionInvoice.objects.select_related(
            "subscription",
            "profile",
            "subscription__service__profile"
        ).annotate(
            service_type=F("subscription__service__service_type")
        ).filter(
            profile__owner_id=self.request.user.owner_id
        ).order_by("-updated_at")
