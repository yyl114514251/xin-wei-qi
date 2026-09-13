"""
go_board.py —— 围棋棋盘与完整规则校验模块

职责：
- 维护棋盘状态（支持 9/13/19 路）
- 规则校验：边界、占用、自杀（禁着点）、打劫（简单劫）
- 提子（吃子）与终局计分（简化数子法）
- GTP 坐标 <-> 内部坐标 转换

设计原则：LLM 只负责"想下哪里"，本模块负责"能不能下"。
任何非法落子都会被本模块拦截并抛出 ValueError。
"""


class GoBoard:
    EMPTY = 0
    BLACK = 1
    WHITE = 2

    def __init__(self, size=19):
        self.size = size
        self.grid = [[self.EMPTY] * size for _ in range(size)]
        self.ko = None            # 打劫禁着点 (x, y)，无则 None
        self.move_num = 0
        self.last_move = None     # (x, y, color)
        self.captured = {self.BLACK: 0, self.WHITE: 0}

    # ---------- 基础工具 ----------

    def in_bounds(self, x, y):
        return 0 <= x < self.size and 0 <= y < self.size

    def neighbors(self, x, y):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                yield nx, ny

    def group_and_liberties(self, x, y, grid=None):
        """返回 (同色连通组坐标集合, 气集合)。grid 可传副本用于模拟。"""
        grid = grid or self.grid
        color = grid[y][x]
        if color == self.EMPTY:
            return set(), set()
        visited = set()
        liberties = set()
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))
            for nx, ny in self.neighbors(cx, cy):
                v = grid[ny][nx]
                if v == self.EMPTY:
                    liberties.add((nx, ny))
                elif v == color and (nx, ny) not in visited:
                    stack.append((nx, ny))
        return visited, liberties

    # ---------- 合法性检查 ----------

    def is_valid(self, x, y):
        """边界 + 空位检查。"""
        return self.in_bounds(x, y) and self.grid[y][x] == self.EMPTY

    def would_be_legal(self, x, y, color):
        """完整合法性：边界、占用、自杀（禁着点）、打劫。"""
        if not self.is_valid(x, y):
            return False
        if self.ko == (x, y):
            return False

        # 模拟落子
        grid = [row[:] for row in self.grid]
        opp = self.WHITE if color == self.BLACK else self.BLACK
        grid[y][x] = color
        captured = 0
        for nx, ny in self.neighbors(x, y):
            if grid[ny][nx] == opp:
                group, libs = self.group_and_liberties(nx, ny, grid)
                if not libs:
                    for gx, gy in group:
                        grid[gy][gx] = self.EMPTY
                    captured += len(group)
        # 己方是否有气（无气且没吃到子 = 自杀）
        _, libs = self.group_and_liberties(x, y, grid)
        if not libs and captured == 0:
            return False
        return True

    # ---------- 落子 ----------

    def play(self, x, y, color):
        """落子并提子。返回提子数。非法则抛出 ValueError。"""
        if not self.in_bounds(x, y):
            raise ValueError("坐标超出棋盘")
        if self.grid[y][x] != self.EMPTY:
            raise ValueError("该位置已有棋子")
        if self.ko == (x, y):
            raise ValueError("打劫：禁止立即回提")

        opp = self.WHITE if color == self.BLACK else self.BLACK
        grid = [row[:] for row in self.grid]
        grid[y][x] = color

        captured = 0
        captured_stones = []  # 记录被提子的坐标，用于打劫判定
        for nx, ny in self.neighbors(x, y):
            if grid[ny][nx] == opp:
                group, libs = self.group_and_liberties(nx, ny, grid)
                if not libs:
                    for gx, gy in group:
                        grid[gy][gx] = self.EMPTY
                    captured += len(group)
                    captured_stones.extend(group)

        _, libs = self.group_and_liberties(x, y, grid)
        if not libs and captured == 0:
            raise ValueError("禁着点：落子后无气（自杀）")

        self.grid = grid
        self.captured[color] += captured
        self.last_move = (x, y, color)
        self.move_num += 1

        # 简单劫判定：恰好提掉对方一颗单子 => 被提子的位置成为新劫点。
        # 若提掉多子或零子，则无劫（多子提不算简单劫）。
        if captured == 1:
            self.ko = captured_stones[0]
        else:
            self.ko = None
        return captured

    # ---------- 终局计分（简化数子法） ----------

    def compute_score(self, komi=7.5):
        """
        简化中国数子法：归属空点只算"只邻接一色"的空组；
        双活（同时邻接两色）的公空不计入任何一方。
        返回 (黑方总子数, 白方总子数)，不含贴目判断。
        """
        visited = set()
        black_area = 0
        white_area = 0
        for y in range(self.size):
            for x in range(self.size):
                if self.grid[y][x] == self.EMPTY and (x, y) not in visited:
                    group = set()
                    stack = [(x, y)]
                    touches_black = False
                    touches_white = False
                    while stack:
                        cx, cy = stack.pop()
                        if (cx, cy) in visited:
                            continue
                        visited.add((cx, cy))
                        group.add((cx, cy))
                        for nx, ny in self.neighbors(cx, cy):
                            v = self.grid[ny][nx]
                            if v == self.EMPTY:
                                if (nx, ny) not in visited:
                                    stack.append((nx, ny))
                            elif v == self.BLACK:
                                touches_black = True
                            elif v == self.WHITE:
                                touches_white = True
                    if touches_black and not touches_white:
                        black_area += len(group)
                    elif touches_white and not touches_black:
                        white_area += len(group)

        black_total = sum(row.count(self.BLACK) for row in self.grid) + black_area
        white_total = sum(row.count(self.WHITE) for row in self.grid) + white_area
        return black_total, white_total

    # ---------- 坐标转换 ----------

    def to_gtp(self, x, y):
        """内部坐标 -> GTP 坐标。GTP 列跳过 I，行从顶部 A1 开始。"""
        col = chr(ord('A') + x)
        if col >= 'I':
            col = chr(ord('A') + x + 1)
        return f"{col}{self.size - y}"

    def from_gtp(self, s):
        """GTP 坐标 -> 内部坐标。返回 (x, y)；'pass' 返回 None。"""
        s = s.strip().upper()
        if s in ('PASS', 'RESIGN'):
            return None
        if len(s) < 2 or not s[0].isalpha() or not s[1:].isdigit():
            raise ValueError(f"无法解析 GTP 坐标: {s}")
        col = s[0]
        if col == 'I':
            raise ValueError("GTP 坐标无 I 列（跳过 I）")
        row = int(s[1:])
        x = ord(col) - ord('A')
        if col > 'I':
            x -= 1
        y = self.size - row
        if not self.in_bounds(x, y):
            raise ValueError(f"坐标 {s} 超出棋盘")
        return x, y

    # ---------- 显示 ----------

    def show(self):
        lines = []
        header = "   " + " ".join(
            chr(ord('A') + i) if i < 8 else chr(ord('A') + i + 1)
            for i in range(self.size)
        )
        lines.append(header)
        for y in range(self.size):
            row = f"{self.size - y:2d} "
            for x in range(self.size):
                v = self.grid[y][x]
                row += ('+' if v == self.EMPTY else ('B' if v == self.BLACK else 'W')) + ' '
            lines.append(row)
        return "\n".join(lines)
