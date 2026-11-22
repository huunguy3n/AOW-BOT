# ruff: noqa: E501, RUF001, RUF002
"""Ten hien thi cua lop nhan dien theo ngon ngu cua tro choi (tieng Viet), de gan nhan bang thuat ngu quen thuoc.

Id lop (vd "intel/btn_attack") la khoa on dinh cho benchmark/ảnh mau; ten hien thi chi dung cho giao dien:
"<Nhom> › <Ten>". Lop do nguoi dung tu go (khong co trong bang) giu nguyen van ban lam id.
Moi anh mau trong templates/ phai co ten o day (tests/unit/test_perception_names.py giu dong bo).
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

SEP = " › "

GROUPS: Mapping[str, str] = MappingProxyType({
    "ally": "Liên minh", "badge": "Chấm đỏ", "build": "Xây dựng", "campaign": "Chiến dịch", "city": "Thành phố",
    "common": "Chung", "daily": "Nhiệm vụ hằng ngày", "defense": "Khiên bảo hộ", "event": "Sự kiện",
    "gather": "Thu thập", "hero": "Tướng", "intel": "Tình báo", "notify": "Thông báo", "play": "Lối chơi",
    "quest": "Nhiệm vụ", "rebels": "Phản quân", "recruit": "Chiêu mộ", "research": "Nghiên cứu",
    "train": "Huấn luyện", "tutorial": "Tân thủ", "welfare": "Phúc lợi",
    "map": "Bản đồ", "menu": "Menu", "ui": "Giao diện",
})

NAMES: Mapping[str, str] = MappingProxyType({
    # --- Liên minh
    "ally/boss_title": "Tiêu đề Boss liên minh", "ally/btn_donate_gold": "Nút Quyên góp (vàng)",
    "ally/btn_gift_claim_all": "Nút Nhận tất cả quà", "ally/btn_open": "Nút mở Liên minh",
    "ally/gift_title": "Tiêu đề Quà liên minh", "ally/icon_gift": "Biểu tượng Quà",
    "ally/mine_collect": "Nút Thu hoạch mỏ liên minh", "ally/mine_go": "Nút Đến mỏ liên minh",
    "ally/tab_affairs": "Thẻ Sự vụ", "ally/tab_main": "Thẻ Chính", "ally/tab_tech": "Thẻ Công nghệ",
    "ally/tech_recommended": "Công nghệ đề xuất", "ally/tile_boss": "Ô Boss", "ally/tile_gifts": "Ô Quà",
    "ally/tile_help": "Ô Trợ giúp", "ally/tile_quests": "Ô Nhiệm vụ", "ally/title": "Tiêu đề Liên minh",
    # --- Chấm đỏ
    "badge/activity": "Chấm đỏ Hoạt động", "badge/bubble": "Bong bóng thông báo", "badge/hero": "Chấm đỏ Tướng",
    "badge/intel": "Chấm đỏ Tình báo", "badge/recruit": "Chấm đỏ Chiêu mộ", "badge/welfare": "Chấm đỏ Phúc lợi",
    # --- Xây dựng
    "build/btn_bar_close": "Nút đóng thanh Xây dựng", "build/btn_construct": "Nút Xây dựng",
    "build/btn_jump": "Nút Nhảy tới", "build/btn_place_ok": "Nút ✓ Đặt công trình", "build/btn_upgrade": "Nút Nâng cấp",
    "build/heal_bubble": "Bong bóng chữa trị (bệnh viện)", "build/btn_upgrade_icon": "Biểu tượng Nâng cấp", "build/card_lock": "Thẻ công trình bị khóa", "build/plot_lock": "Ổ khóa lô đất (chưa mở)",
    "build/icon_builder": "Biểu tượng Thợ xây", "build/icon_hammer": "Biểu tượng Búa xây dựng",
    "build/msg_no_builder": "Thông báo hết thợ xây", "build/title_construct": "Tiêu đề bảng Xây dựng",
    "build/title_hq": "Tiêu đề Nhà chính",
    "build/hq_emblem_a": "Huy hiệu cánh Nhà chính (kiểu mái vòm)",
    "build/hq_emblem_b": "Huy hiệu cánh Nhà chính (kiểu cửa gara)",
    # --- Chiến dịch
    "campaign/battle_hud": "Giao diện trận đánh", "campaign/btn_attack": "Nút Tấn công",
    "campaign/btn_challenge": "Nút Thách đấu", "campaign/btn_done": "Nút Xong (thắng)",
    "campaign/btn_done_lose": "Nút Xong (thua)", "campaign/btn_fight": "Nút Chiến đấu",
    "campaign/btn_idle_claim": "Nút Nhận (treo máy)", "campaign/btn_idle_get": "Nút Lấy thưởng treo máy",
    "campaign/btn_open": "Nút mở Chiến dịch", "campaign/btn_retry": "Nút Thử lại",
    "campaign/pred_win": "Dự đoán Thắng toàn diện", "campaign/res_lose": "Kết quả Thua",
    "campaign/res_win": "Kết quả Thắng", "campaign/title": "Tiêu đề Chiến dịch",
    # --- Thành phố
    "city/res_food": "Tài nguyên nổi: Lương thực", "city/res_metal": "Tài nguyên nổi: Kim loại",
    # --- Chung
    "common/btn_back": "Nút Quay lại (‹)", "common/btn_back2": "Nút Quay lại (kiểu 2)", "common/btn_calendar": "Nút Lịch",
    "common/btn_cancel_exit": "Nút Hủy (thoát game)", "common/btn_close": "Nút Đóng", "common/btn_confirm": "Nút Xác nhận",
    "common/btn_confirm_hero": "Nút Xác nhận tướng", "common/btn_free": "Nút Miễn phí", "common/btn_free_text": "Chữ Miễn phí",
    "common/btn_net_retry": "Nút Thử lại (lỗi mạng)", "common/btn_rebuild": "Nút Xây dựng lại",
    "common/btn_to_city": "Nút về Thành phố", "common/btn_to_world": "Nút ra Bản đồ thế giới", "common/btn_x": "Nút X đóng",
    "common/btn_x_offer": "Nút X (ưu đãi)", "common/btn_x_red": "Nút X đỏ", "common/btn_x_small": "Nút X nhỏ",
    "common/msg_reward": "Bảng Nhận được phần thưởng", "common/tap_to_close": "Chữ Chạm để đóng",
    "common/tap_to_continue": "Chữ Chạm để tiếp tục",
    # --- Nhiệm vụ hằng ngày
    "daily/btn_chest_claim": "Nút Nhận rương", "daily/chest_1": "Rương điểm năng động (đủ điểm)",
    "daily/claim_1": "Nút Nhận nhiệm vụ", "daily/open_1": "Biểu tượng Nhiệm vụ", "daily/tab_2_main": "Thẻ Chính/Chương",
    "daily/tab_3_daily": "Thẻ Hằng ngày",
    # --- Khiên bảo hộ
    "defense/btn_shield_icon": "Biểu tượng Khiên", "defense/btn_use_gems": "Nút dùng Kim cương",
    "defense/row_12h": "Dòng Khiên 12 giờ", "defense/row_1h": "Dòng Khiên 1 giờ", "defense/row_3d": "Dòng Khiên 3 ngày",
    "defense/title": "Tiêu đề Khiên bảo hộ",
    # --- Sự kiện
    "event/btn_popup_claim": "Nút Nhận (popup sự kiện)", "event/heal_btn": "Nút Hồi phục", "event/heal_cnt0": "Hồi phục: số lượng 0",
    "event/timed_login": "Quà đăng nhập theo giờ",
    # --- Thu thập
    "gather/btn_gather": "Nút Thu thập (xe tải)", "gather/btn_level_minus": "Nút – cấp mỏ", "gather/btn_level_plus": "Nút + cấp mỏ",
    "gather/btn_march": "Nút Xuất chinh", "gather/btn_recommended": "Nút Đội hình đề xuất",
    "gather/btn_search": "Nút Tìm kiếm (kính lúp)", "gather/btn_search_go": "Nút Tìm kiếm (xác nhận)",
    "gather/chk_full_off": "Ô chọn Đầy (tắt)", "gather/msg_type_locked": "Thông báo loại mỏ bị khóa",
    "gather/tab_alloy": "Thẻ Hợp kim", "gather/tab_food": "Thẻ Thực phẩm", "gather/tab_metal": "Thẻ Luyện kim",
    "gather/tab_oil": "Thẻ Lọc dầu",
    "gather/march_header": "Khung Hành quân (bản đồ thế giới)",
    "gather/dlg_contested": "Hộp thoại Chỉ huy trưởng khác đang tới mỏ",
    # --- Tướng
    "hero/arrow_up": "Mũi tên Tăng cấp", "hero/btn_book": "Nút Sách kinh nghiệm", "hero/btn_levelup": "Nút Tăng cấp tướng",
    "hero/btn_star": "Nút Sao tướng", "hero/btn_star_up": "Nút Tăng sao", "hero/story_chest": "Rương cốt truyện",
    "hero/title": "Tiêu đề Tướng",
    # --- Tình báo
    "intel/btn_attack": "Nút Tấn công (tình báo)", "intel/btn_energy_plus": "Nút + Năng lượng", "intel/btn_go": "Nút Đến (tình báo)",
    "intel/btn_pickup": "Nút Nhặt", "intel/btn_use_potion": "Nút Dùng thuốc", "intel/marker_done": "Dấu Hoàn thành",
    "intel/marker_fight": "Dấu Chiến đấu", "intel/pin_base": "Ghim Căn cứ", "intel/potion_title": "Tiêu đề Thuốc năng lượng",
    "intel/title": "Tiêu đề Tình báo", "intel/world_pin": "Ghim tình báo trên bản đồ",
    "intel/crate_pin": "Ghim hộp tiếp tế (màn Tình báo)", "intel/crate_pin_world": "Ghim hộp tiếp tế (bản đồ thế giới)",
    # --- Thông báo
    "notify/btn_claim_card": "Nút Nhận thẻ",
    # --- Lối chơi
    "play/arena_free": "Đấu trường: lượt miễn phí", "play/arena_title": "Tiêu đề Đấu trường",
    "play/btn_arena_fight": "Nút Đánh (đấu trường)", "play/btn_arena_recommend": "Nút Đội hình đề xuất (đấu trường)",
    "play/btn_battle": "Nút Chiến đấu", "play/btn_go_loot": "Nút Đến cướp bóc", "play/btn_loot": "Nút Cướp bóc",
    "play/btn_open": "Nút mở Lối chơi", "play/btn_result_close": "Nút đóng bảng kết quả", "play/card_arena": "Thẻ Đấu trường",
    "play/card_mine": "Thẻ Mỏ khoáng sản", "play/mine_chest": "Rương Mỏ khoáng sản", "play/mine_title": "Tiêu đề Mỏ khoáng sản",
    "play/res_arena_win": "Kết quả Thắng (đấu trường)", "play/res_fail": "Kết quả Thất bại", "play/tab_others": "Thẻ Khác",
    # --- Nhiệm vụ
    "quest/banner_icon": "Biểu tượng nhiệm vụ", "quest/btn_go": "Nút Đến (nhiệm vụ)", "quest/duel_red": "Đối thủ lực chiến màu đỏ",
    # --- Phản quân
    "rebels/btn_march_out": "Nút Xuất chinh (phản quân)", "rebels/btn_rally": "Nút Tập kết",
    "rebels/btn_rally_confirm": "Nút Xác nhận tập kết", "rebels/btn_rally_start": "Nút Bắt đầu tập kết",
    "rebels/icon_rally": "Biểu tượng Tập kết", "rebels/label_mech": "Nhãn tên Phản quân Cơ giáp",
    "rebels/legion_title": "Tiêu đề Quân đoàn", "rebels/popup_title": "Tiêu đề bảng Phản quân",
    "rebels/rally_time_title": "Tiêu đề Thời gian tập kết", "rebels/tab_mech": "Thẻ Cơ giáp",
    "rebels/tab_odin": "Thẻ quân đoàn Odin", "rebels/title_mech": "Tiêu đề Phản quân Cơ giáp",
    "rebels/war_empty": "Danh sách chiến tranh trống",
    # --- Chiêu mộ
    "recruit/btn_free": "Nút Chiêu mộ miễn phí", "recruit/btn_one": "Nút Chiêu mộ 1 lần", "recruit/btn_ten": "Nút Chiêu mộ 10 lần",
    "recruit/free_wait": "Chiêu mộ: chờ miễn phí", "recruit/tab_normal": "Thẻ Thường", "recruit/tab_premium": "Thẻ Cao cấp",
    "recruit/title": "Tiêu đề Chiêu mộ",
    # --- Nghiên cứu / Huấn luyện
    "research/btn_detail": "Nút Chi tiết", "research/icon_queue": "Biểu tượng Hàng chờ nghiên cứu",
    "research/title": "Tiêu đề Nghiên cứu",
    "train/btn_goto": "Nút Đến (nhà lính)", "train/btn_train": "Nút Huấn luyện", "train/queue_icon": "Biểu tượng Đội ngũ huấn luyện",
    # --- Tân thủ
    "tutorial/battle_flag": "Cờ trận chạy đường", "tutorial/battle_top": "Trận chạy đường: thanh trên",
    "tutorial/battle_top2": "Trận chạy đường: thanh trên (kiểu 2)", "tutorial/btn_attack_red": "Nút Tấn công đỏ",
    "tutorial/btn_auto_formation": "Nút Đội hình tự động",
    "tutorial/btn_suggest_formation": "Nút Đội hình đề xuất (xuất quân)", "tutorial/btn_build": "Nút Xây dựng (tân thủ)",
    "tutorial/btn_build_ok": "Nút Xây dựng ✓ (tân thủ)", "tutorial/btn_claim": "Nút Nhận (tân thủ)",
    "tutorial/btn_claim_all": "Nút Nhận tất cả (tân thủ)", "tutorial/btn_medkit": "Nút Hộp cứu thương",
    "tutorial/btn_start_game": "Nút Bắt đầu game", "tutorial/dialog_next": "Nút Tiếp (hội thoại)",
    "tutorial/hand_green": "Bàn tay chỉ dẫn xanh", "tutorial/hand_green2": "Bàn tay chỉ dẫn xanh (kiểu 2)",
    "tutorial/icon_explore": "Biểu tượng Thám hiểm", "tutorial/icon_repair": "Biểu tượng Sửa chữa",
    "tutorial/icon_unlock": "Biểu tượng Mở khóa", "tutorial/label_free": "Nhãn Miễn phí",
    "tutorial/marker_v": "Mũi tên V vàng", "tutorial/marker_v_left": "Mũi tên V vàng (trái)",
    "tutorial/marker_v_right": "Mũi tên V vàng (phải)", "tutorial/msg_reward_left": "Thông báo nhận thưởng (trái)",
    "tutorial/supply_box": "Hộp tiếp tế",
    # --- Phúc lợi
    "welfare/btn_basic_reward": "Nút Phần thưởng cơ bản", "welfare/title": "Tiêu đề Phúc lợi",
    # --- Vật thể chưa có ảnh mẫu (thấy trong các chạm tay; id ổn định, tên theo hình ảnh trong game)
    "map/rebel_mech": "Phản quân Cơ giáp (thân)", "map/rebel_elite_leader": "Thủ lĩnh Phiến quân Cấp cao",
    "map/pin_skull": "Ghim bản đồ: đầu lâu", "map/pin_badge_gold": "Ghim bản đồ: huy hiệu vàng",
    "map/pin_swords_purple": "Ghim bản đồ: kiếm chéo tím", "map/resource_node": "Mỏ tài nguyên",
    "map/building": "Công trình trên bản đồ", "map/enemy_hp_bar": "Thanh máu đỏ của mục tiêu",
    "menu/mail": "Biểu tượng Thư", "menu/strategy": "Biểu tượng Chiến lược", "menu/resources": "Biểu tượng Tài nguyên",
    "menu/system": "Thẻ Hệ thống", "ui/hero_card": "Thẻ tướng", "ui/btn_goto": "Nút Đến",
})

EXTRA_IDS: tuple[str, ...] = tuple(k for k in NAMES if k.split("/", 1)[0] in {"map", "menu", "ui"})


def display(cid: str) -> str:
    """'intel/btn_attack' -> 'Tình báo › Nút Tấn công (tình báo)'. Lop la (nguoi dung tu go) -> chinh no."""
    group, _, _ = cid.partition("/")
    if cid in NAMES:
        return f"{GROUPS.get(group, group)}{SEP}{NAMES[cid]}"
    return cid


def display_map(ids: list[str]) -> dict[str, str]:
    """id -> ten hien thi cho moi id da biet (gom lop vat the bo sung)."""
    seen = dict.fromkeys([*ids, *EXTRA_IDS])
    return {c: display(c) for c in seen}


def resolve(text: str, shown: Mapping[str, str]) -> str:
    """Ten hien thi (hoac id) nguoi dung chon/go -> id lop. Khong khop ten nao -> giu nguyen van ban (lop moi)."""
    t = text.strip()
    if t in shown:
        return t
    by_name = {v.casefold(): k for k, v in shown.items()}
    return by_name.get(t.casefold(), t)
