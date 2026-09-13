"""
test_rules.py —— 围棋规则引擎自测

覆盖：坐标转换、提子、禁着点（自杀）、打劫、终局计分。
运行：python test_rules.py
"""

import sys

from go_board import GoBoard

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}")


def test_coords():
    print("== 坐标转换 ==")
    b = GoBoard(19)
    check("A1 <-> (0,18)", b.from_gtp("A1") == (0, 18))
    check("T19 <-> (18,0)", b.from_gtp("T19") == (18, 0))
    check("J4 跳 I 列", b.from_gtp("J4") == (8, 15))
    check("H4 在 I 前", b.from_gtp("H4") == (7, 15))
    try:
        b.from_gtp("I4")
        check("I 列不存在（应抛错）", False)
    except ValueError:
        check("I 列不存在（应抛错）", True)
    check("to_gtp 逆变换", b.to_gtp(0, 18) == "A1")
    check("to_gtp J", b.to_gtp(8, 15) == "J4")


def test_capture():
    print("== 提子 ==")
    b = GoBoard(9)
    # 白子 (4,4) 先落，黑四面包围后提掉
    b.play(4, 4, b.WHITE)
    b.play(4, 3, b.BLACK)   # 上
    b.play(3, 4, b.BLACK)   # 左
    b.play(5, 4, b.BLACK)   # 右
    b.play(4, 5, b.BLACK)   # 下 —— 最后一气，提白
    check("单子被四面包围即提", b.grid[4][4] == b.EMPTY)
    check("黑方提子计数=1", b.captured[b.BLACK] == 1)


def test_suicide():
    print("== 禁着点（自杀）==")
    b = GoBoard(9)
    # 黑占 (0,1)、(1,0)，白在 (0,0) 落子无气且不提子 => 自杀
    b.play(0, 1, b.BLACK)
    b.play(5, 5, b.WHITE)
    b.play(1, 0, b.BLACK)
    check("角落自杀点被拒绝", not b.would_be_legal(0, 0, b.WHITE))
    # 但黑自己下 (0,0) 是允许的（自填眼通常允许，本实现按规则放行）
    check("同点异色仍可落", b.would_be_legal(0, 0, b.BLACK))


def test_ko():
    print("== 打劫 ==")
    b = GoBoard(9)
    # 构造一子劫：白 (1,1) 被黑 (0,1)(1,0)(2,1)(1,2) 围，最后一手黑 (1,2) 提白
    b.play(1, 1, b.WHITE)
    b.play(0, 1, b.BLACK)
    b.play(5, 5, b.WHITE)   # 无关着，调换手顺
    b.play(1, 0, b.BLACK)
    b.play(6, 6, b.WHITE)
    b.play(2, 1, b.BLACK)
    b.play(7, 7, b.WHITE)
    b.play(1, 2, b.BLACK)   # 提掉 (1,1)
    check("提一子形成劫", b.ko is not None)
    check("劫点 (1,1) 被禁止立即回提", not b.would_be_legal(1, 1, b.WHITE))
    # 但其他点不受影响
    check("非劫点不受影响", b.would_be_legal(3, 3, b.WHITE))


def test_score():
    print("== 终局计分 ==")
    b = GoBoard(9)
    # 黑占左上 4x4（16 子），白占右下 2x2（4 子），黑明显领先
    for x in range(4):
        for y in range(4):
            b.grid[y][x] = b.BLACK
    for x in range(7, 9):
        for y in range(7, 9):
            b.grid[y][x] = b.WHITE
    black, white = b.compute_score()
    check("黑方计分>白方", black > white)
    check("黑=16 白=4", black == 16 and white == 4)


if __name__ == "__main__":
    test_coords()
    test_capture()
    test_suicide()
    test_ko()
    test_score()
    print(f"\n结果: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
