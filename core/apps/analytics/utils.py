from core.apps.analytics.models import MatchActivity, BrandActivity
from core.apps.brand.models import Brand


def log_match_activity(initiator: Brand, target: Brand, is_match: bool) -> None:
    """
    Writes like/match/collab user activity to DB.

    Should be called in corresponding api methods after entry creation.
    Should be used inside an atomic transaction, so that it logged activity only if instance was successfully created.
    """
    MatchActivity.objects.create(
        initiator=initiator,
        target=target,
        is_match=is_match,
    )


def log_brand_activity(brand: Brand, action: str) -> None:
    """
    Writes brand activity to DB.

    Should be called in corresponding api methods after action is performed.
    Should be used inside an atomic transaction, so that it logged activity only if instance was successfully created.

    Args:
        brand: brand object that performed action
        action: name of the action. Must be one of the BrandActivity.ACTION_CHOICES
    """
    BrandActivity.objects.create(brand=brand, action=action)
