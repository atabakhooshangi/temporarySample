from django.contrib import admin

from services.models import (
    Service,
    DailyROI,
    ROIHistory,
    Subscription,
    SubscriptionInvoice,
    DailyAggregatedPnl,
)
from .roi import ROIHistoryAdmin, DailyROIAdmin, DailyAggregatedPnlAdmin
from .service import ServiceAdmin, ServiceRank
from .subscription import SubscriptionAdmin, SubscriptionInvoiceAdmin
from ..models.service import SignalService

admin.site.register(Service, ServiceAdmin)
admin.site.register(SignalService, ServiceRank)
admin.site.register(DailyROI, DailyROIAdmin, )
admin.site.register(ROIHistory, ROIHistoryAdmin, )
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(SubscriptionInvoice, SubscriptionInvoiceAdmin)
admin.site.register(DailyAggregatedPnl, DailyAggregatedPnlAdmin)
