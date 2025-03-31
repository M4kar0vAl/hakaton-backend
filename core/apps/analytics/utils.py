from core.apps.analytics.models import BrandActivity
from core.apps.brand.models import Brand, Collaboration


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
