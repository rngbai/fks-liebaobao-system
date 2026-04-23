from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db_mysql import (
    GEM_SCALE,
    calculate_guarantee_actual_receive_x10,
    calculate_guarantee_seller_total_cost_x10,
    get_connection,
    grant_order_commission,
    init_database_and_tables,
    lock_wallet,
)


def _create_user(conn, user_key, nick_name, invited_by_user_id=None):
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO users (user_key, openid, nick_name, avatar_url, account, beast_id, phone, email, invited_by_user_id)
            VALUES (%s, '', %s, '', '', '', '', '', %s)
            ''',
            (user_key, nick_name, invited_by_user_id)
        )
        user_id = int(cursor.lastrowid)
        cursor.execute('SELECT * FROM users WHERE id=%s LIMIT 1', (user_id,))
        return cursor.fetchone()


def _set_wallet_zero(conn, user_id):
    wallet = lock_wallet(conn, user_id)
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE user_wallets
            SET gem_balance=0,
                gem_balance_x10=0,
                locked_gems=0,
                locked_gems_x10=0,
                total_recharged=0,
                total_recharged_x10=0,
                total_spent=0,
                total_spent_x10=0,
                total_earned=0,
                total_earned_x10=0,
                commission_pending_x10=0,
                updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
            ''',
            (user_id,)
        )
    return wallet


def main():
    init_database_and_tables()

    seller_total_cost_x10 = calculate_guarantee_seller_total_cost_x10(100, 5)
    actual_receive_x10 = calculate_guarantee_actual_receive_x10(100, 5)
    assert seller_total_cost_x10 == 100 * GEM_SCALE + 5, seller_total_cost_x10
    assert actual_receive_x10 == 100 * GEM_SCALE - 5, actual_receive_x10

    marker = datetime.now().strftime('%Y%m%d%H%M%S%f')

    with get_connection(autocommit=False) as conn:
        try:
            l2_user = _create_user(conn, f'test_l2_{marker}', 'L2推广员')
            l1_user = _create_user(conn, f'test_l1_{marker}', 'L1推广员', invited_by_user_id=l2_user['id'])
            seller_user = _create_user(conn, f'test_seller_{marker}', '成交卖家', invited_by_user_id=l1_user['id'])

            _set_wallet_zero(conn, l2_user['id'])
            _set_wallet_zero(conn, l1_user['id'])
            _set_wallet_zero(conn, seller_user['id'])

            order_row = {
                'order_no': f'GUA_TEST_{marker}',
                'seller_user_id': seller_user['id'],
            }
            grant_order_commission(conn, order_row)

            with conn.cursor() as cursor:
                cursor.execute(
                    'SELECT gem_balance_x10, total_earned_x10 FROM user_wallets WHERE user_id=%s LIMIT 1',
                    (l1_user['id'],)
                )
                l1_wallet = cursor.fetchone() or {}
                cursor.execute(
                    'SELECT gem_balance_x10, total_earned_x10 FROM user_wallets WHERE user_id=%s LIMIT 1',
                    (l2_user['id'],)
                )
                l2_wallet = cursor.fetchone() or {}
                cursor.execute(
                    '''
                    SELECT reward_type, reward_amount_x10
                    FROM promotion_commission_logs
                    WHERE order_no=%s
                    ORDER BY id ASC
                    ''',
                    (order_row['order_no'],)
                )
                reward_rows = cursor.fetchall() or []

            assert int(l1_wallet.get('gem_balance_x10') or 0) == 3, l1_wallet
            assert int(l1_wallet.get('total_earned_x10') or 0) == 3, l1_wallet
            assert int(l2_wallet.get('gem_balance_x10') or 0) == 2, l2_wallet
            assert int(l2_wallet.get('total_earned_x10') or 0) == 2, l2_wallet

            reward_map = {row['reward_type']: int(row['reward_amount_x10'] or 0) for row in reward_rows}
            assert reward_map.get('l1_commission') == 3, reward_rows
            assert reward_map.get('l2_commission') == 2, reward_rows
            assert 'first_order_bonus' not in reward_map, reward_rows
            assert 'monthly_tier' not in reward_map, reward_rows
            assert 'monthly_top5' not in reward_map, reward_rows

            print('promotion and fee rules verified')
        finally:
            conn.rollback()


if __name__ == '__main__':
    main()
