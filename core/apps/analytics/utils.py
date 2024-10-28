from core.apps.analytics.models import MatchActivity, BrandActivity
from core.apps.brand.models import Brand, Collaboration


def log_match_activity(initiator: Brand, target: Brand, is_match: bool, collab: Collaboration | None = None) -> None:
    """
    Writes like/match/collab user activity to DB.

    Should be called in corresponding api methods after entry creation.
    Should be used inside an atomic transaction, so that it logged activity only if instance was successfully created.

    If is_match = False, then it is 'like' action
    If is_match = True, then it is 'like' action, that led to match
    If collab != None (NULL in DB), then one of the brands reported collaboration in corresponding match
    If collab != None, then initiator - who reported collab, target - participant of collab
    """
    MatchActivity.objects.create(
        initiator=initiator,
        target=target,
        is_match=is_match,
        collab=collab
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
