from bot.utils.telegram import create_inline


def support_kb(support_id: int, msg_id):
    return create_inline(
        [
            ['✅ Решено', 'call', f'admin_support_decided:{support_id}:{msg_id}'],
            ['❌ Закрыть', 'call', f'admin_support_closed:{support_id}:{msg_id}'],
            ['🛠 Передать разработчику', 'call', f'admin_support_call_dev:{support_id}:{msg_id}'],
        ],
        2
    )
