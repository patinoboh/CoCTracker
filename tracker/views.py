import json
import hashlib
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .imports import extract_level_records
from .models import GameAccount, GameDataSnapshot, ShortcutToken, Upgrade, UpgradeOption, Village


def _token_user(request: HttpRequest):
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        token_hash = hashlib.sha256(authorization[7:].encode()).hexdigest()
        token = ShortcutToken.objects.filter(
            token_hash=token_hash,
            revoked_at__isnull=True,
        ).select_related("user").first()
        if token is not None:
            ShortcutToken.objects.filter(pk=token.pk).update(last_used_at=timezone.now())
            return token.user
    return request.user if request.user.is_authenticated else None


@login_required
def dashboard(request: HttpRequest):
    accounts = GameAccount.objects.filter(user=request.user).prefetch_related("villages")
    upgrades = Upgrade.objects.filter(
        option__village__game_account__user=request.user,
        status=Upgrade.ACTIVE,
    ).select_related("option__village__game_account")
    return render(request, "tracker/dashboard.html", {"accounts": accounts, "upgrades": upgrades})


@login_required
@require_POST
def import_account_data(request: HttpRequest, account_id: int):
    account = GameAccount.objects.filter(id=account_id, user=request.user).first()
    if account is None:
        return JsonResponse({"error": "Account not found."}, status=404)
    try:
        payload = json.loads(request.POST["json_data"])
        if not isinstance(payload, (dict, list)):
            raise ValueError
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Enter a valid JSON object or array."}, status=400)
    snapshot = GameDataSnapshot.objects.create(
        account=account,
        raw_data=payload,
        extracted_levels=extract_level_records(payload),
    )
    return JsonResponse({"id": snapshot.id, "extracted_records": len(snapshot.extracted_levels)})


def _unauthorized():
    return JsonResponse({"error": "Authentication required."}, status=401)


@require_GET
def shortcut_accounts(request: HttpRequest):
    user = _token_user(request)
    if user is None:
        return _unauthorized()
    accounts = GameAccount.objects.filter(user=user)
    return JsonResponse({"items": [{"id": account.id, "title": account.name} for account in accounts]})


@require_GET
def shortcut_villages(request: HttpRequest, account_id: int):
    user = _token_user(request)
    if user is None:
        return _unauthorized()
    villages = Village.objects.filter(game_account_id=account_id, game_account__user=user)
    return JsonResponse(
        {
            "items": [
                {"id": village.id, "title": village.name or village.get_village_type_display()}
                for village in villages
            ]
        }
    )


@require_GET
def shortcut_options(request: HttpRequest, village_id: int):
    user = _token_user(request)
    if user is None:
        return _unauthorized()
    category = request.GET.get("category")
    options = UpgradeOption.objects.filter(village_id=village_id, village__game_account__user=user)
    if category:
        options = options.filter(category=category)
    return JsonResponse(
        {
            "items": [
                {
                    "id": str(option.id),
                    "title": option.display_name,
                    "subtitle": f"Level {option.current_level} → {option.current_level + 1}",
                    "current_level": option.current_level,
                    "suggested_to_level": option.current_level + 1,
                    "duration_minutes": option.duration_minutes,
                }
                for option in options
            ]
        }
    )


@require_POST
def shortcut_upgrades(request: HttpRequest):
    user = _token_user(request)
    if user is None:
        return _unauthorized()
    try:
        payload = json.loads(request.body)
        option = UpgradeOption.objects.get(
            id=payload["upgrade_target_id"],
            village__game_account__user=user,
        )
        to_level = int(payload.get("to_level", option.current_level + 1))
        duration_minutes = int(payload["duration_minutes"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, UpgradeOption.DoesNotExist):
        return JsonResponse({"error": "Invalid upgrade payload."}, status=400)

    now = timezone.now()
    upgrade = Upgrade.objects.create(
        option=option,
        from_level=to_level - 1,
        to_level=to_level,
        started_at=now,
        finishes_at=now + timedelta(minutes=duration_minutes),
    )
    option.current_level = to_level
    option.save(update_fields=["current_level"])
    return JsonResponse(
        {
            "id": str(upgrade.id),
            "title": f"{option.display_name} {upgrade.from_level} → {upgrade.to_level}",
            "finishes_at": upgrade.finishes_at.isoformat(),
        },
        status=201,
    )


@require_POST
def shortcut_import_account_data(request: HttpRequest, account_id: int):
    user = _token_user(request)
    if user is None:
        return _unauthorized()
    account = GameAccount.objects.filter(id=account_id, user=user).first()
    if account is None:
        return JsonResponse({"error": "Account not found."}, status=404)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, (dict, list)):
            raise ValueError
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Request body must be a JSON object or array."}, status=400)
    snapshot = GameDataSnapshot.objects.create(
        account=account,
        raw_data=payload,
        extracted_levels=extract_level_records(payload),
    )
    return JsonResponse(
        {
            "id": snapshot.id,
            "account_id": account.id,
            "imported_at": snapshot.imported_at.isoformat(),
            "extracted_records": len(snapshot.extracted_levels),
        },
        status=201,
    )
