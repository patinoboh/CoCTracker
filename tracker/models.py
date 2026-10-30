import uuid
import hashlib
import secrets

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class GameAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="game_accounts")
    name = models.CharField(max_length=100)
    player_tag = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name


class GameDataSnapshot(models.Model):
    account = models.ForeignKey(GameAccount, on_delete=models.CASCADE, related_name="data_snapshots")
    raw_data = models.JSONField()
    extracted_levels = models.JSONField(default=dict)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-imported_at"]

    def __str__(self) -> str:
        return f"{self.account.name} import at {self.imported_at:%Y-%m-%d %H:%M}"


class ShortcutToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shortcut_tokens")
    name = models.CharField(max_length=100)
    token_prefix = models.CharField(max_length=12)
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def create_token(cls, user: User, name: str) -> tuple["ShortcutToken", str]:
        raw_token = f"coc_live_{secrets.token_urlsafe(32)}"
        token = cls.objects.create(
            user=user,
            name=name,
            token_prefix=raw_token[:12],
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        )
        return token, raw_token

    def __str__(self) -> str:
        return f"{self.name} ({self.token_prefix})"


class Village(models.Model):
    HOME = "home_village"
    BUILDER_BASE = "builder_base"
    VILLAGE_TYPES = [
        (HOME, "Home Village"),
        (BUILDER_BASE, "Builder Base"),
    ]

    game_account = models.ForeignKey(GameAccount, on_delete=models.CASCADE, related_name="villages")
    village_type = models.CharField(max_length=30, choices=VILLAGE_TYPES)
    name = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["village_type", "id"]
        constraints = [
            models.UniqueConstraint(fields=["game_account", "village_type"], name="one_village_type_per_account")
        ]

    def __str__(self) -> str:
        return self.name or self.get_village_type_display()


class UpgradeOption(models.Model):
    BUILDING = "building"
    HERO = "hero"
    LABORATORY = "laboratory"
    PET = "pet"
    CATEGORIES = [
        (BUILDING, "Building"),
        (HERO, "Hero"),
        (LABORATORY, "Laboratory"),
        (PET, "Pet"),
    ]

    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="upgrade_options")
    category = models.CharField(max_length=30, choices=CATEGORIES)
    name = models.CharField(max_length=100)
    instance_number = models.PositiveIntegerField(null=True, blank=True)
    current_level = models.PositiveIntegerField(default=1)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["category", "name", "instance_number", "id"]

    @property
    def display_name(self) -> str:
        if self.instance_number:
            return f"{self.name} {self.instance_number}"
        return self.name


class Upgrade(models.Model):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    STATUSES = [
        (ACTIVE, "Active"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    option = models.ForeignKey(UpgradeOption, on_delete=models.PROTECT, related_name="upgrades")
    from_level = models.PositiveIntegerField()
    to_level = models.PositiveIntegerField()
    started_at = models.DateTimeField(default=timezone.now)
    finishes_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUSES, default=ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["finishes_at"]

    @property
    def is_active(self) -> bool:
        return self.status == self.ACTIVE
