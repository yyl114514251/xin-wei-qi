"""
gtp_server.py —— GTP（Go Text Protocol）协议服务器

这是整个项目与"其他自制围棋 AI"互通的窗口。
任何实现了 GTP 的引擎 / 界面（Sabaki、Lizzie、其他自研 AI）都可以
通过标准输入输出与本程序对弈：

    python gtp_server.py

标准 GTP 命令逐行输入，逐行输出（"= 响应"）。
"""

import sys

from go_board import GoBoard
from llm_go_player import LLMGoPlayer


class GTPEngine:
    def __init__(self):
        self.size = 19
        self.board = GoBoard(self.size)
        self.komi = 7.5

    # ---------- 响应 ----------

    def reply(self, ok=True, msg=""):
        return ("= " if ok else "? ") + msg + "\n\n"

    # ---------- 命令处理 ----------

    def handle(self, line):
        parts = line.strip().split()
        if not parts:
            return ""
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "protocol_version":
            return self.reply(msg="2")
        elif cmd == "name":
            return self.reply(msg="GoLLM-Playground")
        elif cmd == "version":
            return self.reply(msg="0.1.0")
        elif cmd == "boardsize":
            n = int(args[0])
            if n not in (9, 13, 19):
                return self.reply(False, "unsupported board size")
            self.size = n
            self.board = GoBoard(n)
            return self.reply()
        elif cmd == "clear_board":
            self.board = GoBoard(self.size)
            return self.reply()
        elif cmd == "komi":
            self.komi = float(args[0])
            return self.reply()
        elif cmd == "play":
            color = 1 if args[0].upper() == "B" else 2
            pos = self.board.from_gtp(args[1])
            if pos is None:  # pass
                self.board.ko = None
                return self.reply()
            try:
                self.board.play(pos[0], pos[1], color)
                return self.reply()
            except ValueError as e:
                return self.reply(False, str(e))
        elif cmd == "genmove":
            color = 1 if args[0].upper() == "B" else 2
            move = self.genmove(color)
            if move is None:
                return self.reply(msg="pass")
            x, y = move
            self.board.play(x, y, color)
            return self.reply(msg=self.board.to_gtp(x, y))
        elif cmd == "showboard":
            return self.reply(msg=self.board.show())
        elif cmd == "final_score":
            b, w = self.board.compute_score()
            # 简化：黑贴 7.5 目（数子法近似 3.75 子）
            margin = (b - 3.75) - w
            winner = "B" if margin > 0 else "W"
            return self.reply(msg=f"{winner}+{abs(margin):.1f}")
        elif cmd == "quit":
            return None
        else:
            # 未知命令按 GTP 规范返回空成功
            return self.reply()

    def genmove(self, color):
        """调用 LLM 选点；非法落子自动转为 pass。"""
        player = LLMGoPlayer(color, self.size)
        move = player.genmove(self.board)
        if move is None:
            return None
        x, y = move
        if not self.board.would_be_legal(x, y, color):
            print(f"[规则拦截] LLM 给出的 {self.board.to_gtp(x, y)} 非法，自动 pass",
                  file=sys.stderr)
            return None
        return move

    # ---------- 主循环 ----------

    def run(self):
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            result = self.handle(line)
            if result is None:
                break
            sys.stdout.write(result)
            sys.stdout.flush()


if __name__ == "__main__":
    GTPEngine().run()
