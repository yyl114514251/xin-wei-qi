"""
web_server.py —— 网页版对局后端（Flask）

提供 HTTP API 给 webui/index.html 调用：
  GET  /             返回网页前端
  GET  /api/state    返回棋盘状态、轮次、是否终局
  POST /api/move     人类落子（白），参数 {"x":..,"y":..}
  POST /api/ai       让 LLM（黑）落子
  POST /api/reset    重置对局
  POST /api/pass     人类 pass

运行：
  python web_server.py
然后浏览器打开 http://127.0.0.1:5000
"""

import threading

from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

from go_board import GoBoard
from llm_go_player import LLMGoPlayer

load_dotenv()

app = Flask(__name__, static_folder="webui", static_url_path="/static")

SIZE = 19
BOARD_SIZE_LABEL = 19


class GameState:
    def __init__(self):
        self.board = GoBoard(SIZE)
        self.ai_color = 1       # 黑
        self.human_color = 2    # 白
        self.turn = 1           # 黑先
        self.passes = 0
        self.over = False
        self.result = ""
        self.lock = threading.Lock()
        self.ai_player = LLMGoPlayer(self.ai_color, SIZE)

    def to_dict(self):
        ko = self.board.ko
        return {
            "grid": self.board.grid,
            "size": self.board.size,
            "turn": self.turn,
            "over": self.over,
            "result": self.result,
            "ko": None if ko is None else list(ko),
            "last_move": self.board.last_move,
            "captured": self.board.captured,
            "move_num": self.board.move_num,
        }

    def check_end(self):
        """连续两次 pass 视为终局。"""
        if self.passes >= 2 and not self.over:
            b, w = self.board.compute_score()
            margin = (b - 3.75) - w
            self.over = True
            self.result = f"黑 {b} : 白 {w}（黑贴7.5目），" + (
                f"黑胜 {margin:.1f}" if margin > 0 else f"白胜 {-margin:.1f}"
            )
        return self.over


state = GameState()


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/state", methods=["GET"])
def api_state():
    with state.lock:
        return jsonify(state.to_dict())


@app.route("/api/move", methods=["POST"])
def api_move():
    """人类（白）落子。"""
    with state.lock:
        if state.over:
            return jsonify({"ok": False, "msg": "对局已结束，请先重置"})
        if state.turn != state.human_color:
            return jsonify({"ok": False, "msg": "还没轮到你"})

        data = request.get_json() or {}
        try:
            x = int(data["x"])
            y = int(data["y"])
        except (KeyError, TypeError, ValueError):
            return jsonify({"ok": False, "msg": "参数错误"})

        if not state.board.would_be_legal(x, y, state.human_color):
            return jsonify({"ok": False, "msg": "非法落子（占用/禁着点/打劫）"})

        state.board.play(x, y, state.human_color)
        state.passes = 0
        state.turn = state.ai_color
        return jsonify({"ok": True, "state": state.to_dict()})


@app.route("/api/ai", methods=["POST"])
def api_ai():
    """LLM（黑）落子。非法输出会被规则拦截并自动 pass。"""
    with state.lock:
        if state.over:
            return jsonify({"ok": False, "msg": "对局已结束，请先重置"})
        if state.turn != state.ai_color:
            return jsonify({"ok": False, "msg": "还没轮到 AI"})

        move = state.ai_player.genmove(state.board)
        if move is None:
            state.passes += 1
            state.turn = state.human_color
            state.check_end()
            return jsonify({"ok": True, "move": "PASS", "state": state.to_dict()})

        x, y = move
        if not state.board.would_be_legal(x, y, state.ai_color):
            # LLM 输出非法落子：规则拦截，自动 pass
            state.passes += 1
            state.turn = state.human_color
            state.check_end()
            return jsonify({
                "ok": True, "move": "PASS",
                "blocked": state.board.to_gtp(x, y),
                "state": state.to_dict(),
            })

        state.board.play(x, y, state.ai_color)
        state.passes = 0
        state.turn = state.human_color
        return jsonify({"ok": True, "move": state.board.to_gtp(x, y), "state": state.to_dict()})


@app.route("/api/pass", methods=["POST"])
def api_pass():
    """人类 pass。"""
    with state.lock:
        if state.over:
            return jsonify({"ok": False, "msg": "对局已结束"})
        if state.turn != state.human_color:
            return jsonify({"ok": False, "msg": "还没轮到你"})
        state.passes += 1
        state.turn = state.ai_color
        state.check_end()
        return jsonify({"ok": True, "state": state.to_dict()})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    global state
    state = GameState()
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("GoLLM-Playground WebUI: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
