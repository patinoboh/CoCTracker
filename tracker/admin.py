from django.contrib import admin

from .models import GameAccount, GameDataSnapshot, ShortcutToken, Upgrade, UpgradeOption, Village

admin.site.register(GameAccount)
admin.site.register(GameDataSnapshot)
admin.site.register(ShortcutToken)
admin.site.register(Village)
admin.site.register(UpgradeOption)
admin.site.register(Upgrade)
