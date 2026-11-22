from bot.modules.reddots import is_hud_dot


def test_real_badges_kept():
    for d in [(147, 576), (64, 629), (64, 682), (525, 730), (530, 796), (356, 893), (134, 35)]:
        assert is_hud_dot(d), d


def test_scene_and_chat_dots_dropped():
    # mai do / chu thap do cong trinh (i2 2026-11-22) va huy hieu chat
    for d in [(423, 773), (320, 798), (304, 791), (49, 326)]:
        assert not is_hud_dot(d), d
