from fastapi import Header, HTTPException
from sqlalchemy import text
from app.core.database import get_db
import json


db = get_db()
def get_current_user(report_key: str = Header(...)):

    query = """
    SELECT id, name, region, area, warehouse
    FROM users
    WHERE uuid = :report_key
    AND status = 1
    """

    try:

        user = db.execute(text(query), {"report_key": report_key}).fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid report key")

        user_dict = dict(user._mapping)

        user_dict["region"] = json.loads(user_dict["region"] or "[]")
        user_dict["area"] = json.loads(user_dict["area"] or "[]")
        user_dict["warehouse"] = json.loads(user_dict["warehouse"] or "[]")

        return user_dict

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))