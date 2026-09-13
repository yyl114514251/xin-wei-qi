"""
llm_go_player.py —— LLM 围棋棋手

职责：调用大模型 API（智谱 / 千帆），输入当前棋盘文本，
     让模型输出一个 GTP 落子坐标（或 pass）。
     只负责"思考选点"，不负责规则判断（规则由 go_board.py 校验）。

支持 provider：
  - zhipu  : 智谱 AI 开放平台（默认，OpenAI 兼容接口）
  - qianfan: 百度千帆（OpenAI 兼容接口 v2）
"""

import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()


class LLMGoPlayer:
    def __init__(self, color, size=19, provider=None):
        self.color = color  # 1=黑 2=白
        self.size = size
        self.provider = provider or os.getenv("LLM_PROVIDER", "zhipu")

        self.zhipu_key = os.getenv("ZHIPU_API_KEY", "")
        self.zhipu_model = os.getenv("ZHIPU_MODEL", "glm-4-flash")

        self.qianfan_key = os.getenv("QIANFAN_API_KEY", "")
        self.qianfan_model = os.getenv("QIANFAN_MODEL", "ernie-4.0")

    # ---------- 棋盘 -> 文本 ----------

    def board_to_text(self, board):
        rows = []
        for y in range(board.size):
            cells = []
            for x in range(board.size):
                v = board.grid[y][x]
                cells.append('.' if v == 0 else ('B' if v == 1 else 'W'))
            rows.append(" ".join(cells))
        return "\n".join(rows)

    def build_prompt(self, board):
        me = "黑(B)" if self.color == 1 else "白(W)"
        board_str = self.board_to_text(board)
        ko = board.ko
        ko_str = f"打劫禁着点：{board.to_gtp(*ko)}" if ko else "无打劫禁着点"
        prompt = (
            f"你是一个围棋业余1~3段水平的棋手，正在下一盘{self.size}路围棋。\n"
            f"你执{me}，现在轮到你落子。\n"
            f"当前棋盘（. = 空，B = 黑棋，W = 白棋，左上角为 A1，列跳过 I）：\n"
            f"{board_str}\n"
            f"{ko_str}\n"
            f"\n"
            f"请只输出一个合法的落子位置（GTP 格式，如 D4、K10）；"
            f"如果认为局面已结束则输出 pass。\n"
            f"只输出坐标或 pass，不要输出任何其他文字。"
        )
        return prompt

    # ---------- API 调用 ----------

    def call_llm(self, prompt):
        if self.provider == "zhipu":
            url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.zhipu_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.zhipu_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 32,
            }
        elif self.provider == "qianfan":
            url = "https://qianfan.baidubce.com/v2/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.qianfan_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.qianfan_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 32,
            }
        else:
            raise ValueError(f"未知 provider: {self.provider}")

        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    # ---------- 对外接口：生成一手 ----------

    def genmove(self, board):
        """
        让 LLM 选一手。
        返回 (x, y) 表示落子；返回 None 表示 pass / 调用失败 / 输出无法解析。
        不负责合法性终审（由调用方再校验）。
        """
        prompt = self.build_prompt(board)
        try:
            raw = self.call_llm(prompt)
        except Exception as e:  # 网络/限流/解析失败一律保守 pass
            print(f"[LLM 调用失败] {type(e).__name__}: {e}")
            return None

        # 从输出中提取 GTP 坐标（列 A-T，行 1-19）
        m = re.search(r"\b[A-Ta-t](?:19|1[0-9]|[1-9])\b", raw)
        if not m:
            print(f"[LLM 输出无法解析为坐标] {raw!r}，视为 pass")
            return None
        gtp = m.group(0)
        try:
            return self.from_gtp(gtp)
        except Exception:
            return None

    def from_gtp(self, s):
        """本地坐标解析（与 go_board 保持一致，供独立使用）。"""
        s = s.strip().upper()
        col = s[0]
        row = int(s[1:])
        x = ord(col) - ord('A')
        if col > 'I':
            x -= 1
        y = self.size - row
        return x, y


if __name__ == "__main__":
    from go_board import GoBoard

    board = GoBoard(19)
    player = LLMGoPlayer(1, 19)
    move = player.genmove(board)
    print("LLM 建议:", "pass" if move is None else board.to_gtp(*move))
