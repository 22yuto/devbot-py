from fastapi import APIRouter
from app.models import Item

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Hello World"}
@router.get("/items/{item_id}", response_model=Item)
async def read_item(item_id: int, q: str | None = None):
    return {"id": item_id, "name": f"Item {item_id}"}