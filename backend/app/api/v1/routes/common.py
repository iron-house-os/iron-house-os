from pydantic import BaseModel


class PlaceholderItem(BaseModel):
    id: str
    name: str
    status: str = "placeholder"


class PlaceholderList(BaseModel):
    items: list[PlaceholderItem]
    total: int


def placeholder_list(module_name: str) -> PlaceholderList:
    item = PlaceholderItem(
        id=f"{module_name}-placeholder",
        name=f"{module_name.title()} placeholder",
    )
    return PlaceholderList(items=[item], total=1)
