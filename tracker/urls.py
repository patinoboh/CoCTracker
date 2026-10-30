from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("accounts/<int:account_id>/import", views.import_account_data, name="import-account-data"),
    path("api/shortcut/accounts", views.shortcut_accounts, name="shortcut-accounts"),
    path(
        "api/shortcut/accounts/<int:account_id>/villages",
        views.shortcut_villages,
        name="shortcut-villages",
    ),
    path(
        "api/shortcut/villages/<int:village_id>/options",
        views.shortcut_options,
        name="shortcut-options",
    ),
    path("api/shortcut/upgrades", views.shortcut_upgrades, name="shortcut-upgrades"),
    path(
        "api/shortcut/accounts/<int:account_id>/import",
        views.shortcut_import_account_data,
        name="shortcut-import-account-data",
    ),
]
