"""
Authentication routes.

Phase 3 spec: FastAPI routes for signup, login, and user profile.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.db import models
from app.db.schemas import (
    UserCreate, UserRead, UserLogin, Token,
    RefreshTokenRequest, UserUpdate, PasswordChange
)
from app.auth.service import (
    create_user,
    authenticate_user,
    create_user_access_token
)
from app.auth.dependencies import get_current_user

router = APIRouter()


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def signup(
    user_create: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user account.
    
    Args:
        user_create: UserCreate schema with email and password
        db: Database session
    
    Returns:
        UserRead schema with created user info
    
    Raises:
        HTTPException: 400 if email already registered or validation fails
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Validate password length
        if not user_create.password or len(user_create.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Normalize email - create a new UserCreate with normalized email
        from app.db.schemas import UserCreate
        normalized_email = user_create.email.lower().strip()
        normalized_user_create = UserCreate(
            email=normalized_email,
            password=user_create.password
        )
        
        user = create_user(db, normalized_user_create)
        logger.info(f"User created: {user.email} (ID: {user.id})")
        return UserRead.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create account: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login(
    user_login: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login and get access token.
    
    Args:
        user_login: UserLogin schema with email and password
        db: Database session
    
    Returns:
        Token schema with access_token and token_type
    
    Raises:
        HTTPException: 401 if email or password is incorrect
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Normalize email (case-insensitive)
        normalized_email = user_login.email.lower().strip() if user_login.email else ""
        
        if not normalized_email or not user_login.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )
        
        user = authenticate_user(db, normalized_email, user_login.password)
        if user is None:
            logger.warning(f"Login failed for email: {normalized_email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = create_user_access_token(user)
        logger.info(f"Login successful for user: {user.email} (ID: {user.id})")
        return Token(access_token=access_token, token_type="bearer")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: models.User = Depends(get_current_user)
):
    """
    Get current authenticated user profile.
    
    Args:
        current_user: Current user from JWT token (via dependency)
    
    Returns:
        UserRead schema with user info
    """
    return UserRead.model_validate(current_user)


# Additional endpoints (beyond Phase 3 spec)
# These are kept for backward compatibility but not part of Phase 3 requirements

@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token (beyond Phase 3)."""
    from datetime import timedelta
    from app.auth.service import (
        verify_refresh_token,
        create_refresh_token_record,
        revoke_refresh_token
    )
    from app.auth.jwt import create_access_token, create_refresh_token
    from app.config import get_settings
    
    settings = get_settings()
    try:
        user = verify_refresh_token(db, token_request.refresh_token)
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=access_token_expires
        )
        
        # Optionally rotate refresh token
        new_refresh_token = create_refresh_token()
        revoke_refresh_token(db, token_request.refresh_token)
        create_refresh_token_record(db, user.id, new_refresh_token)
        
        return Token(access_token=access_token, token_type="bearer")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.put("/me", response_model=UserRead)
async def update_me(
    user_update: UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile (beyond Phase 3)."""
    from app.auth.service import get_user_by_email
    
    if user_update.email:
        # Check if email is already taken
        existing = get_user_by_email(db, user_update.email)
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = user_update.email
    
    db.commit()
    db.refresh(current_user)
    return UserRead.model_validate(current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_change: PasswordChange,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password (beyond Phase 3)."""
    from app.auth.service import verify_password, update_user_password
    from app.utils.validation import validate_password
    
    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    is_valid, error_msg = validate_password(password_change.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    update_user_password(db, current_user, password_change.new_password)
    return None


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete current user account (beyond Phase 3)."""
    from app.auth.service import delete_user_account
    delete_user_account(db, current_user)
    return None

