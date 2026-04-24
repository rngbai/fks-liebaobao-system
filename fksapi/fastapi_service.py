from __future__ import annotations

from typing import Any

from config import token
from db_mysql import (
    build_feedback_payload,
    build_home_content_payload,
    build_promotion_payload,
    build_recharge_state,
    build_transfer_state,
    build_user_stats,
    find_guarantee_order,
    get_connection,
    get_live_game_credentials,
    get_or_create_user,
    list_guarantee_orders,
    list_wallet_records,
    serialize_guarantee_row,
    serialize_user,
    serialize_wallet,
)
from recharge_verify_server import RECEIVER_BEAST_ID, RECEIVER_BEAST_NICK, check_user_active


class FastAPIService:
    def get_recharge_state_payload(self, user_key: str, profile: dict[str, Any] | None = None):
        with get_connection(autocommit=False) as conn:
            user_row, wallet_row = get_or_create_user(conn, user_key, profile)
            data = self.build_live_recharge_state(conn, user_row, wallet_row)
            conn.commit()
            return data

    def get_user_profile_payload(self, user_key: str, profile: dict[str, Any] | None = None):
        with get_connection(autocommit=False) as conn:
            user_row, wallet_row = get_or_create_user(conn, user_key, profile)
            payload = {
                "user": serialize_user(user_row),
                "wallet": serialize_wallet(wallet_row),
                "stats": build_user_stats(conn, user_row["id"]),
            }
            conn.commit()
            return payload

    def get_transfer_state_payload(self, user_key: str, profile: dict[str, Any] | None = None, limit: int = 20):
        with get_connection(autocommit=False) as conn:
            user_row, wallet_row = get_or_create_user(conn, user_key, profile)
            payload = build_transfer_state(conn, user_row, wallet_row, limit=limit)
            conn.commit()
            return payload

    def get_guarantee_list_payload(self, user_key: str, profile: dict[str, Any] | None = None, limit: int = 20):
        with get_connection(autocommit=False) as conn:
            user_row, _ = get_or_create_user(conn, user_key, profile)
            orders = list_guarantee_orders(conn, user_id=user_row["id"], role="seller", limit=limit)
            wallet_row = get_or_create_user(conn, user_key, profile)[1]
            payload = {
                "wallet": serialize_wallet(wallet_row),
                "orders": orders,
            }
            conn.commit()
            return payload

    def get_guarantee_detail_payload(
        self,
        user_key: str,
        order_no: str,
        profile: dict[str, Any] | None = None,
    ):
        with get_connection(autocommit=False) as conn:
            user_row, _ = get_or_create_user(conn, user_key, profile)
            order_row = find_guarantee_order(conn, order_no)
            if not order_row:
                raise ValueError("未找到担保单")
            wallet_row = get_or_create_user(conn, user_key, profile)[1]
            seller_user_id = int(order_row.get("seller_user_id") or 0)
            buyer_user_id = int(order_row.get("buyer_user_id") or 0)
            current_user_id = int(user_row.get("id") or 0)
            can_match = (order_row.get("status") == "pending") and seller_user_id != current_user_id
            viewer_role = "seller" if seller_user_id == current_user_id else ("buyer" if buyer_user_id == current_user_id else "guest")
            payload = {
                "order": serialize_guarantee_row(order_row),
                "wallet": serialize_wallet(wallet_row),
                "viewerRole": viewer_role,
                "canMatch": can_match,
            }
            conn.commit()
            return payload

    def get_feedback_payload(
        self,
        user_key: str,
        profile: dict[str, Any] | None = None,
        limit: int = 20,
        mine_only: bool = False,
        feedback_type: str | None = None,
        scene: str = "",
    ):
        with get_connection(autocommit=False) as conn:
            user_row, _ = get_or_create_user(conn, user_key, profile)
            payload = build_feedback_payload(
                conn,
                user_row,
                limit=limit,
                mine_only=mine_only,
                feedback_type=feedback_type,
                scene=scene,
            )
            conn.commit()
            return payload

    def get_promotion_payload(self, user_key: str, profile: dict[str, Any] | None = None, limit: int = 20):
        with get_connection(autocommit=False) as conn:
            user_row, _ = get_or_create_user(conn, user_key, profile)
            payload = build_promotion_payload(conn, user_row, limit=limit)
            conn.commit()
            return payload

    def get_home_content_payload(self):
        with get_connection(autocommit=False) as conn:
            payload = build_home_content_payload(conn)
            conn.commit()
            return payload

    def get_live_credentials(self, conn=None):
        if conn is not None:
            return get_live_game_credentials(conn, RECEIVER_BEAST_ID, token, env_user_name=RECEIVER_BEAST_NICK)
        with get_connection(autocommit=False) as connection:
            uid, tk, token_type, user_name = get_live_game_credentials(
                connection,
                RECEIVER_BEAST_ID,
                token,
                env_user_name=RECEIVER_BEAST_NICK,
            )
            connection.commit()
        return uid, tk, token_type, user_name

    def build_live_recharge_state(self, conn, user_row, wallet_row):
        live_uid, _, _, live_user_name = self.get_live_credentials(conn)
        receiver_beast_id = str(live_uid or RECEIVER_BEAST_ID).strip()
        receiver_beast_nick = str(live_user_name or RECEIVER_BEAST_NICK).strip()
        return build_recharge_state(conn, user_row, wallet_row, receiver_beast_id, receiver_beast_nick)

    def get_wallet_records_payload(self, user_key: str, profile: dict[str, Any] | None = None, limit: int = 50):
        with get_connection(autocommit=False) as conn:
            user_row, wallet_row = get_or_create_user(conn, user_key, profile)
            check_user_active(user_row)
            records = list_wallet_records(conn, user_row["id"], limit)
            transfer_payload = build_transfer_state(conn, user_row, wallet_row, limit=10)
            wallet = serialize_wallet(wallet_row)
            conn.commit()
        return {
            "user": transfer_payload["user"],
            "balance": wallet["gemBalance"],
            "lockedGems": wallet["lockedGems"],
            "totalRecharged": wallet["totalRecharged"],
            "totalSpent": wallet["totalSpent"],
            "totalEarned": wallet["totalEarned"],
            "pendingTransfer": transfer_payload["transfer"]["pendingRequest"],
            "transferHistory": transfer_payload["transfer"]["history"],
            "records": records,
        }
