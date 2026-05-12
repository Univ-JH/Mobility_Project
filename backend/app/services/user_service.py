from app.repositories import user_repo
from app.schemas.user_dto import UserProfileResponse, RideHistoryResponse, RideHistoryItemDto

async def get_user_profile(user_id: str) -> UserProfileResponse:
    user = await user_repo.get_user_by_id(user_id)
    if not user:
        # Mock user creation if not exists for prototyping
        from app.repositories.models import User
        user = User(userId=user_id, email=f"{user_id}@example.com", name="Test User")
        await user_repo.create_user(user)
        
    return UserProfileResponse(
        name=user.name,
        email=user.email,
        safetyScore=user.safetyScore,
        appSettings=user.appSettings
    )

async def get_ride_history(user_id: str) -> RideHistoryResponse:
    history_data = await user_repo.get_ride_history_for_user(user_id)
    items = [RideHistoryItemDto(**item) for item in history_data]
    return RideHistoryResponse(history=items)
