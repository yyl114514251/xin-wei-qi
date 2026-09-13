"""
main.py —— 本地控制台人机对战

人类执一方，LLM 执另一方，直接在终端下棋。
落子用 GTP 坐标（如 D4、K10），输入 pass 停一手，输入 quit 退出。
"""

from go_board import GoBoard
from llm_go_player import LLMGoPlayer


def get_human_color():
    while True:
        c = input("你执黑(B)还是白(W)？[b/w] ").strip().lower()
        if c.startswith("b"):
            return 1
        if c.startswith("w"):
            return 2
        print("输入 b 或 w")


def main():
    board = GoBoard(19)
    human = get_human_color()
    ai_color = 3 - human
    ai = LLMGoPlayer(ai_color, 19)

    print("\n=== GoLLM-Playground 人机对战 ===")
    print("落子用 GTP 坐标（如 D4），pass 停一手，quit 退出\n")

    turn = 1  # 黑先
    passes = 0
    resign = False

    while True:
        print(board.show())
        print()
        if turn == human:
            s = input("你的落子: ").strip()
            if s.lower() in ("quit", "exit", "resign"):
                print("你认输了。")
                resign = True
                break
            if s.lower() == "pass":
                passes += 1
                if passes >= 2:
                    break
                turn = 3 - turn
                continue
            try:
                pos = board.from_gtp(s)
                if pos is None:
                    print("无法解析该坐标，请重试（如 D4）")
                    continue
                n = board.play(pos[0], pos[1], human)
                if n:
                    print(f"你提了 {n} 子")
                passes = 0
                turn = 3 - turn
            except ValueError as e:
                print(f"非法落子：{e}")
        else:
            print("LLM 思考中…")
            move = ai.genmove(board)
            if move is None:
                print("LLM 停手 (pass)")
                passes += 1
                if passes >= 2:
                    break
            else:
                x, y = move
                if not board.would_be_legal(x, y, ai_color):
                    print("[规则拦截] LLM 落子非法，自动 pass")
                    passes += 1
                    if passes >= 2:
                        break
                else:
                    n = board.play(x, y, ai_color)
                    print(f"LLM 落子 {board.to_gtp(x, y)}" + (f"，提 {n} 子" if n else ""))
                    passes = 0
            turn = 3 - turn

    if not resign:
        b, w = board.compute_score()
        print("\n=== 终局（简化数子法，黑贴 7.5 目）===")
        print(f"黑方：{b} 子，白方：{w} 子")
        margin = (b - 3.75) - w
        if margin > 0:
            print(f"黑胜 {abs(margin):.1f} 目")
        else:
            print(f"白胜 {abs(margin):.1f} 目")
    print("对局结束")


if __name__ == "__main__":
    main()
