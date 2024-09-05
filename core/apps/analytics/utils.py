from core.apps.analytics.models import MatchActivity
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
