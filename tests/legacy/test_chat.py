import os

import cv2
import numpy as np
import pytest

from bot.modules import chat

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures", "chat_list_i0.png")


def test_unread_badge_synthetic_circle_and_rejects_bar():
    img = np.full((960, 540, 3), 40, np.uint8)
    cv2.circle(img, (500, 200), 15, (225, 152, 53), -1)             # BGR cua xanh duong sang (H~102)
    cv2.rectangle(img, (40, 350), (92, 366), (225, 152, 53), -1)    # thanh xanh dai (avatar), khong phai huy hieu
    cv2.circle(img, (200, 400), 15, (225, 152, 53), -1)             # tron nhung x < 380 (khong phai cot huy hieu)
    assert chat.unread_rows(img) == [(500, 200)]


@pytest.mark.fixtures
def test_unread_badge_real_list_screen():
    img = cv2.imread(FIX)
    if img is None:
        pytest.skip("thieu anh fixture")
    assert chat.unread_rows(img) == [(504, 145)]
