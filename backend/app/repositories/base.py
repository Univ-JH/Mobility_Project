from typing import TypeVar, Generic, Type, Optional, List, Any
from beanie import Document, PydanticObjectId
from pydantic import BaseModel

T = TypeVar("T", bound=Document)

class BaseRepository(Generic[T]):
    """
    제네릭 Base Repository.
    모든 도메인별 Repository에서 상속받아 공통 CRUD를 재사용할 수 있습니다.
    """
    def __init__(self, model: Type[T]):
        self.model = model

    async def get(self, id: Any) -> Optional[T]:
        """
        문서 ID로 조회. ObjectID 뿐만 아니라 커스텀 ID 필드도 고려 가능하도록 구성.
        """
        if isinstance(id, str):
            try:
                id = PydanticObjectId(id)
            except Exception:
                pass
        return await self.model.get(id)

    async def get_all(self, limit: int = 100, skip: int = 0) -> List[T]:
        """
        전체 리스트 페이징 조회.
        """
        return await self.model.find_all().skip(skip).limit(limit).to_list()

    async def create(self, document: T) -> T:
        """
        단일 문서 생성.
        """
        await document.insert()
        return document

    async def delete(self, id: Any) -> bool:
        """
        문서 ID로 삭제. 삭제 성공 시 True 반환.
        """
        doc = await self.get(id)
        if doc:
            await doc.delete()
            return True
        return False
