from fastapi import APIRouter

from app.api.v1.routes.common import PlaceholderList, placeholder_list

router = APIRouter()


@router.get("", response_model=PlaceholderList)
def list_rfqs() -> PlaceholderList:
    return placeholder_list("rfqs")
