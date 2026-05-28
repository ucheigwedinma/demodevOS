from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
                    ContractAmendmentViewSet,
                    ContractClauseViewSet,
                    ContractViewSet,
                    GoodsReceiptFlatViewSet,
                    GoodsReceiptItemViewSet,
                    GoodsReceiptViewSet,
                    POItemViewSet,
                    PRItemViewSet,
                    ProcurementOverviewView,
                    SpendAnalyticsView,
                    PurchaseOrderViewSet,
                    PurchaseRequisitionViewSet,
                    RequestForQuotationViewSet,
                    RFQQuoteViewSet,
                    VendorCategoryViewSet,
                    VendorViewSet,
)

vendor_category_router = DefaultRouter()
vendor_category_router.register(r"", VendorCategoryViewSet, basename="vendor-category")

vendor_router = DefaultRouter()
vendor_router.register(r"", VendorViewSet, basename="vendor")

pr_router = DefaultRouter()
pr_router.register(r"", PurchaseRequisitionViewSet, basename="purchase-requisition")

pr_item_router = DefaultRouter()
pr_item_router.register(r"", PRItemViewSet, basename="pr-item")

po_router = DefaultRouter()
po_router.register(r"", PurchaseOrderViewSet, basename="purchase-order")

po_item_router = DefaultRouter()
po_item_router.register(r"", POItemViewSet, basename="po-item")

grn_router = DefaultRouter()
grn_router.register(r"", GoodsReceiptViewSet, basename="goods-receipt")

grn_item_router = DefaultRouter()
grn_item_router.register(r"", GoodsReceiptItemViewSet, basename="grn-item")

grn_flat_router = DefaultRouter()
grn_flat_router.register(r"", GoodsReceiptFlatViewSet, basename="goods-receipt-flat")

rfq_router = DefaultRouter()
rfq_router.register(r"", RequestForQuotationViewSet, basename="rfq")

rfq_quote_router = DefaultRouter()
rfq_quote_router.register(r"", RFQQuoteViewSet, basename="rfq-quote")

contract_router = DefaultRouter()
contract_router.register(r"", ContractViewSet, basename="contract")

contract_amendment_router = DefaultRouter()
contract_amendment_router.register(r"", ContractAmendmentViewSet, basename="contract-amendment")

contract_clause_router = DefaultRouter()
contract_clause_router.register(r"", ContractClauseViewSet, basename="contract-clause")

urlpatterns = [
    path("overview/", ProcurementOverviewView.as_view(), name="procurement-overview"),
    path("spend-analytics/", SpendAnalyticsView.as_view(), name="spend-analytics"),
    path("vendor-categories/", include(vendor_category_router.urls)),
    path("vendors/", include(vendor_router.urls)),
    path("requisitions/", include(pr_router.urls)),
    path("requisitions/<int:pr_pk>/items/", include(pr_item_router.urls)),
    path("purchase-orders/", include(po_router.urls)),
    path("purchase-orders/<int:po_pk>/items/", include(po_item_router.urls)),
    path("purchase-orders/<int:po_pk>/goods-receipts/", include(grn_router.urls)),
    path("purchase-orders/<int:po_pk>/goods-receipts/<int:grn_pk>/items/", include(grn_item_router.urls)),
    path("goods-receipts/", include(grn_flat_router.urls)),
    path("rfqs/", include(rfq_router.urls)),
    path("rfqs/<int:rfq_pk>/quotes/", include(rfq_quote_router.urls)),
    path("contracts/", include(contract_router.urls)),
    path("contracts/<int:contract_pk>/amendments/", include(contract_amendment_router.urls)),
    path("contracts/<int:contract_pk>/clauses/", include(contract_clause_router.urls)),
]
