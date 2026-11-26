"""Tinh bao (buoc rieng, chay sau cham do, truoc gui quan) - chu du an yeu cau 2026-11-18.

Chay MOI luot (khong can icon co cham do): nhan nhiem vu da xong, danh/nhat nhiem vu con lai khi du nang luong
(het thi dung Thuoc The Luc neu bat notify.intel_use_potions; KHONG BAO GIO mua bang kim cuong).
Logic dung chung notify.intel().
"""
import logging
from bot.modules import notify

log = logging.getLogger("aow")


def run(ctx):
    nc = ctx.cfg.get("notify", {})
    if notify.intel_stopped(ctx):      # P13j: khong ve thanh pho, khong cham gi
        log.info("Tinh bao: da het quan doan ranh trong luot ghe nay -> bo qua buoc")
        return 0
    if not ctx.find("campaign/btn_open"):      # P9-9: icon Tinh bao co ca tren ban do the gioi -> khong bat ve thanh pho
        ctx.ensure_city()
    if not ctx.find("campaign/btn_open"):
        log.info("Khong thay icon Chien dich/Tinh bao (chua mo khoa?) - bo qua")
        return 0
    try:
        n = notify.intel(ctx, nc.get("intel_max", 20))
    finally:
        notify.leave(ctx)
        ctx.ensure_city()                       # quy uoc: module xong thi ve thanh pho
    log.info("Tinh bao: %d nhiem vu", n)
    return n
