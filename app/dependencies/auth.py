from fastapi import Header, HTTPException, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db


api_key_header = APIKeyHeader(
    name="x-api-key",
    auto_error=False
)


def get_current_user(api_key: str = Depends(api_key_header), db: Session = Depends(get_db)):

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="x-api-key header missing"
        )

    get_report_keys = """
          SELECT user_id
                FROM report_keys
                WHERE TRIM(api_key) = TRIM(:api_key)
                  AND is_active = true
                LIMIT 1
        """

    report_key = (
        db.execute(
            text(get_report_keys),
            {"api_key": api_key},
        ).mappings().first()
    )
    
    if not report_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    get_user_permissions =  """
            SELECT
                id,
                name,
                company,
                region,
                route,
                salesman,
                outlet_channel,
                item_category_id,
                item_id
            FROM users
            WHERE id = :user_id
            LIMIT 1
        """

    user = (
        db.execute(
            text(get_user_permissions),
            {"user_id": report_key["user_id"]},
        ).mappings().first()
    )

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return dict(user)
