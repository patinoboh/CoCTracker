import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import GameAccount, GameDataSnapshot, ShortcutToken, UpgradeOption, Village


class ShortcutApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="password")
        self.client.login(username="tester", password="password")
        self.account = GameAccount.objects.create(user=self.user, name="Main")
        self.village = Village.objects.create(
            game_account=self.account,
            village_type=Village.HOME,
            name="Home Village",
        )
        self.option = UpgradeOption.objects.create(
            village=self.village,
            category=UpgradeOption.HERO,
            name="Barbarian King",
            current_level=80,
            duration_minutes=120,
        )

    def test_accounts_and_options_are_dynamic(self):
        response = self.client.get(reverse("shortcut-accounts"))
        self.assertEqual(response.json()["items"], [{"id": self.account.id, "title": "Main"}])

        response = self.client.get(
            reverse("shortcut-options", kwargs={"village_id": self.village.id}),
            {"category": UpgradeOption.HERO},
        )
        self.assertEqual(response.json()["items"][0]["suggested_to_level"], 81)

    def test_upgrade_creation_advances_option_level(self):
        response = self.client.post(
            reverse("shortcut-upgrades"),
            data=json.dumps(
                {
                    "upgrade_target_id": self.option.id,
                    "to_level": 81,
                    "duration_minutes": 120,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.option.refresh_from_db()
        self.assertEqual(self.option.current_level, 81)
        self.assertGreaterEqual(
            (timezone.datetime.fromisoformat(response.json()["finishes_at"]) - timezone.now()).total_seconds(),
            timedelta(minutes=119).total_seconds(),
        )

    def test_api_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("shortcut-accounts"))
        self.assertEqual(response.status_code, 401)

    def test_api_accepts_device_token_without_session(self):
        _, raw_token = ShortcutToken.create_token(self.user, "iPhone")
        self.client.logout()
        response = self.client.get(
            reverse("shortcut-accounts"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["title"], "Main")

    def test_account_json_import_preserves_payload_and_extracts_levels(self):
        payload = {"heroes": [{"name": "Barbarian King", "level": 80}]}
        response = self.client.post(
            reverse("import-account-data", kwargs={"account_id": self.account.id}),
            {"json_data": json.dumps(payload)},
        )
        self.assertEqual(response.status_code, 200)
        snapshot = GameDataSnapshot.objects.get(account=self.account)
        self.assertEqual(snapshot.raw_data, payload)
        self.assertEqual(snapshot.extracted_levels[0]["level"], 80)

    def test_shortcut_can_import_account_json(self):
        _, raw_token = ShortcutToken.create_token(self.user, "iPhone")
        self.client.logout()
        response = self.client.post(
            reverse("shortcut-import-account-data", kwargs={"account_id": self.account.id}),
            data=json.dumps({"buildings": [{"name": "Cannon", "level": 10}]}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["extracted_records"], 1)
