import sys
import random
import pygame

"""
Snake Game (Pygame) – 難度 + 隨機加速道具 + 隨機邊界傳送
=============================================================
功能總覽
---------
* **三段難度**：
  1. 普通
  2. 障礙物定時移動
  3. 障礙與食物皆定時移動
* **隨機加速道具**（閃電⚡）：吃到後 N 秒內速度提升
* **隨機邊界傳送**：撞牆不 Game‑Over，而是隨機出現在任一邊界
* 其他：得分顯示、頭尾互換、身體截斷、加速逐漸遞增等

測試環境：pygame 2.5.2、Python ≥3.10
跑法：
```bash
pip install pygame
python snake_game.py
```
"""

# ────────────────────────────────────────────────────────────────────
# 全域參數
# ────────────────────────────────────────────────────────────────────
CELL_SIZE         = 15
GRID_W, GRID_H    = 50, 50
SCOREBAR_H        = 40
FPS_BASE          = 8
OBSTACLE_COUNT    = 25
INITIAL_FOOD      = 3
NEW_FOOD_EVENT_MS = 2500
BOOST_EVENT_MS    = 10000          # 新閃電道具產生間隔(ms)
BOOST_DURATION    = 450            # 加速持續 frame 數（依 FPS 計）
BOOST_FPS_INC     = 4
SPAWN_BOMB = pygame.USEREVENT + 5
C_BOMB = (139, 0, 0)
BOMB_EFFECT = 3  # 被扣掉的長度
CONFUSE_INTERVAL  = 12000          # 每 12 秒嘗試產生一個迷惑道具
# 新增 Boss 模式參數
BOSS_MODE = False
BOSS_SHRINK_INTERVAL = 10000  # 每 10 秒減 1 格
BOMB_MOVE_INTERVAL = 3000     # 每 3 秒移動炸彈
SPAWN_FAKE_FOOD = pygame.USEREVENT + 7
MOVE_BOMBS = pygame.USEREVENT + 8


# 難度 (障礙刷新 ms, 食物刷新 ms)
DIFFICULTY_SETTINGS = {
    1: {"obst_ms": 0,     "food_ms": 0,     "obst_count": 10, "food_count": 5, "bomb_count": 1, "confuse_count": 1, "portal_pairs": 1},
    2: {"obst_ms": 4000,  "food_ms": 0,     "obst_count": 20, "food_count": 4, "bomb_count": 2, "confuse_count": 1, "portal_pairs": 2},
    3: {"obst_ms": 3000,  "food_ms": 3000,  "obst_count": 35, "food_count": 3, "bomb_count": 3, "confuse_count": 2, "portal_pairs": 3},
}

speed_increment   = True
randomized_start  = True

WINDOW_W = CELL_SIZE * GRID_W
WINDOW_H = CELL_SIZE * GRID_H + SCOREBAR_H

# 色彩
C_BG       = (30, 30, 30)
C_GRID     = (50, 50, 50)
C_BOUND    = (200, 200, 200)
C_SNAKE    = (0, 220, 0)
C_FOOD     = (240, 30, 30)
C_OBST     = (120, 120, 120)
C_BOOST    = (255, 215, 0)
C_TEXT     = (255, 255, 255)
C_GAMEOVER = (255, 80, 80)
C_MENU     = (180, 180, 180)
C_SNAKE_CONFUSE = (100, 100, 255)  # 混亂狀態下的蛇色（藍紫色）
C_FAKE_FOOD = (50, 50, 50)
C_FAKE_OBST = (80, 80, 80)

PORTAL_COLORS = [
    (0, 255, 255),  # 青藍
    (255, 0, 255),  # 粉紫
    (255, 255, 0),  # 黃
    (0, 255, 128),  # 綠藍
]

DIRS = {
    pygame.K_w: (0, -1), pygame.K_UP: (0, -1),
    pygame.K_s: (0, 1),  pygame.K_DOWN: (0, 1),
    pygame.K_a: (-1, 0), pygame.K_LEFT: (-1, 0),
    pygame.K_d: (1, 0),  pygame.K_RIGHT: (1, 0),
}

# 自定義事件
SPAWN_FOOD     = pygame.USEREVENT + 1
MOVE_OBSTACLES = pygame.USEREVENT + 2
MOVE_FOODS     = pygame.USEREVENT + 3
SPAWN_BOOST    = pygame.USEREVENT + 4

SPAWN_CONFUSE = pygame.USEREVENT + 6
CONFUSE_DURATION = 5 * FPS_BASE  # 持續 5 秒（依 FPS 計）
C_CONFUSE = (100, 100, 255)  # 淡藍紫


# ────────────────────────────────────────────────────────────────────
# 遊戲類別
# ────────────────────────────────────────────────────────────────────
class SnakeGame:
    def __init__(self):
        self.waiting_start = True
        self.paused = False

        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("Snake Game – Plus Mode")
        self.clock = pygame.time.Clock()
        self.font  = pygame.font.SysFont("consolas", 20)
        self.small_font = pygame.font.SysFont("consolas", 14)

        self.difficulty = self.choose_difficulty()
        self.player_name = self.get_player_name()

        # ✅ 然後取得對應難度設定
        settings = DIFFICULTY_SETTINGS[self.difficulty]
        self.obstacle_count = settings["obst_count"]
        self.initial_food   = settings["food_count"]
        self.max_bombs      = settings["bomb_count"]
        self.max_confuses = settings["confuse_count"]
        self.bombs          = set()
        self.portals = []  # 傳送門位置對
        self.num_portal_pairs = settings["portal_pairs"]


        # ✅ 現在才開始設 timer 沒問題
        pygame.time.set_timer(SPAWN_BOMB, 8000)

        self.confuses = set()
        self.confuse_remaining = 0
        pygame.time.set_timer(SPAWN_CONFUSE, 12000)  # 每 12 秒嘗試產生一次



        # 設定計時器（只有 >0 才會設）
        if settings["obst_ms"] > 0:
            pygame.time.set_timer(MOVE_OBSTACLES, settings["obst_ms"])
        if settings["food_ms"] > 0:
            pygame.time.set_timer(MOVE_FOODS, settings["food_ms"])

        if self.difficulty >= 2:
            pygame.time.set_timer(SPAWN_CONFUSE, CONFUSE_INTERVAL)
        
        # 初始化 Boss 計時器
        if BOSS_MODE:
            pygame.time.set_timer(pygame.USEREVENT + 9, BOSS_SHRINK_INTERVAL)
            pygame.time.set_timer(MOVE_BOMBS, BOMB_MOVE_INTERVAL)
            pygame.time.set_timer(SPAWN_FAKE_FOOD, 5000)

        self.fake_food = set()
        self.invisible_obstacles = set()
        if BOSS_MODE:
            self.invisible_obstacles = set(random.sample(available, 8))



        # 一律設定的固定計時器
        pygame.time.set_timer(SPAWN_FOOD, NEW_FOOD_EVENT_MS)
        pygame.time.set_timer(SPAWN_BOOST, BOOST_EVENT_MS)

        self.reset()

    # ────────────────────────────────────────────────
    # 選單
    # ────────────────────────────────────────────────
    def get_player_name(self):
        name = ""
        asking = True
        prompt = self.font.render("Enter Your Name:", True, C_TEXT)
        while asking:
            self.screen.fill(C_BG)
            self.screen.blit(prompt, (WINDOW_W//3, WINDOW_H//2 - 30))
            input_txt = self.font.render(name + "_", True, C_TEXT)
            self.screen.blit(input_txt, (WINDOW_W//3, WINDOW_H//2))
            pygame.display.flip()
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_RETURN and name.strip():
                        return name.strip()[:10]
                    elif e.key == pygame.K_BACKSPACE:
                        name = name[:-1]
                    else:
                        if len(name) < 10 and e.unicode.isprintable():
                            name += e.unicode


    def choose_difficulty(self):
        title = self.font.render("Select Difficulty", True, C_MENU)
        opts  = ["Level 1", "Level 2 ", "Level 3", "Boss Mode"]
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if e.type == pygame.KEYDOWN:
                    if e.key in (pygame.K_1, pygame.K_KP1): return 1
                    if e.key in (pygame.K_2, pygame.K_KP2): return 2
                    if e.key in (pygame.K_3, pygame.K_KP3): return 3
                    if e.key in (pygame.K_4, pygame.K_KP4):
                        global BOSS_MODE
                        BOSS_MODE = True
                        return 3
            self.screen.fill(C_BG)
            self.screen.blit(title, ((WINDOW_W-title.get_width())//2, 80))
            for i, txt in enumerate(opts):
                label = self.font.render(txt, True, C_MENU)
                self.screen.blit(label, (WINDOW_W//2-110, 150+i*40))
            pygame.display.flip(); self.clock.tick(15)

    # ────────────────────────────────────────────────
    # 初始化 / 重開
    # ────────────────────────────────────────────────
    def reset(self):
    # 畫面顯示
        self.screen.fill(C_BG)
        loading_msg = self.font.render("Generating map... Please wait", True, C_TEXT)
        self.screen.blit(loading_msg, ((WINDOW_W - loading_msg.get_width()) // 2, WINDOW_H // 2))
        pygame.display.flip()

        pygame.time.wait(1000)# 顯示 1 秒

        pygame.event.clear() # ✅ 清空事件佇列，避免卡在輸入或 quit

        # 初始蛇身
        tries = 0
        while tries < 1000:
            if randomized_start:
                head = (random.randint(5, GRID_W-6), random.randint(5, GRID_H-6))
                dir_idx = random.choice(list(DIRS.values()))
            else:
                head, dir_idx = (GRID_W//2, GRID_H//2), (1, 0)

            body = (head[0] - dir_idx[0], head[1] - dir_idx[1])
            next_step = (head[0] + dir_idx[0], head[1] + dir_idx[1])

            if all(0 <= x < GRID_W and 0 <= y < GRID_H for x, y in [body, next_step]):
                break
            tries += 1

        # 把 dir_idx 展開成 dx, dy
        dx, dy = dir_idx
        # 假設方向是 (0, 1) 往下
        self.snake = [head,
                      (head[0] - dx, head[1] - dy),
                      (head[0] - 2*dx, head[1] - 2*dy)]
        self.direction = (dx, dy)

        self.pending_growth = 0
        self.age = 0
        self.game_over = False



        # 建立保護區域（蛇頭、身體、頭前一步）
        protect_area = set(self.snake)
        hx, hy = self.snake[0]
        dx, dy = self.direction
        protect_area.add((hx + dx, hy + dy))

        # 建立所有合法位置
        all_grid = {(x, y) for x in range(GRID_W) for y in range(GRID_H)}
        available = list(all_grid - protect_area)

        # 檢查可用空格是否足夠
        total_needed = self.obstacle_count + self.initial_food
        if len(available) < total_needed:
            print("⚠ 地圖太小或障礙數量太多，請減少設定")
            pygame.quit(); sys.exit()

        # 障礙與食物
        sampled = random.sample(available, total_needed)
        self.obstacles = set(sampled[:self.obstacle_count])
        self.food = set(sampled[self.obstacle_count:self.obstacle_count+self.initial_food])
        self.boosts = set()

        self.confuses = set()

        # 重設速度
        self.base_fps = FPS_BASE
        self.fps = FPS_BASE
        self.boost_remaining = 0

        self.spawn_portals()  # ✅ 這裡呼叫剛剛出錯的 spawn_portals

        # ✅ 馬上顯示遊戲畫面（不會卡在 loading）
        self.render()

        if self.paused and not self.game_over:
            pause_msg = self.font.render("PAUSED – Press P to resume", True, C_MENU)
            self.screen.blit(pause_msg, ((WINDOW_W - pause_msg.get_width()) // 2, WINDOW_H // 2))

        pygame.display.flip()  # ✅ 顯示畫面更新

        self.waiting_start = True  # 等待玩家第一次按鍵才開始動



    # ────────────────────────────────────────────────
    # 主迴圈
    # ────────────────────────────────────────────────
    def run(self):
        while True:
            self.handle_events()
            if not self.game_over and not self.paused:
                self.update()
            self.render()
            self.clock.tick(self.fps)

    # ────────────────────────────────────────────────
    # 事件處理
    # ────────────────────────────────────────────────
    def handle_events(self):

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

                if e.key == pygame.K_p:
                    self.paused = not self.paused

                if e.key in DIRS:
                    nd = DIRS[e.key]

                    # 🌀 如果進入混亂狀態，上下左右全部反轉
                    if self.confuse_remaining > 0:
                        nd = (-nd[0], -nd[1])


                    if self.waiting_start or (nd[0] != -self.direction[0] or nd[1] != -self.direction[1]):
                        self.direction = nd
                        self.waiting_start = False


                if self.game_over and e.key == pygame.K_r:
                    self.reset()
            if e.type == SPAWN_BOMB and not self.game_over and len(self.bombs) < self.max_bombs:
                self.spawn_bomb()
            if e.type == SPAWN_CONFUSE and not self.game_over:
                # 限制增加速度，不要太快增加太多
                if len(self.confuses) < self.max_confuses + self.age // 300:
                    self.spawn_confuse()
            if e.type == SPAWN_FOOD and not self.game_over:
                self.spawn_food()
            if e.type == SPAWN_BOOST and not self.game_over and len(self.boosts) < 1:
                self.spawn_boost()
            if e.type == MOVE_OBSTACLES and not self.game_over:
                self.relocate_obstacles()
            if e.type == MOVE_FOODS and not self.game_over:
                self.relocate_foods()

    def flash_explosion(self, times=3, interval=100):
        for _ in range(times):
            # 閃紅色
            self.screen.fill((255, 0, 0))
            pygame.display.flip()
            pygame.time.delay(interval)
        
            # 閃背景色
            self.render()
            pygame.display.flip()
            pygame.time.delay(interval)

    # ────────────────────────────────────────────────
    # 核心更新
    # ────────────────────────────────────────────────
    def update(self):


        if self.waiting_start:
            return  # 還沒按鍵，不更新位置

        # FPS 自增
        self.age += 1
        if speed_increment and self.age % 150 == 0:
            self.base_fps += 1
            if self.boost_remaining == 0:
                self.fps = self.base_fps

        # Boost 時間減少
        if self.boost_remaining > 0:
            self.boost_remaining -= 1
            if self.boost_remaining == 0:
                self.fps = self.base_fps

        if self.confuse_remaining > 0:
            self.confuse_remaining -= 1


        # 計算下一格
        hx, hy = self.snake[0]
        dx, dy = self.direction
        nx, ny = hx+dx, hy+dy

        # 邊界處理：對側傳送
        if nx < 0:
            nx = GRID_W - 1
        elif nx >= GRID_W:
            nx = 0
        if ny < 0:
            ny = GRID_H - 1
        elif ny >= GRID_H:
            ny = 0


        new_head = (nx, ny)

        # 傳送門處理：進入後立即傳送到另一邊
        if new_head in self.portals:
            idx = self.portals.index(new_head)
            other_idx = 1 - idx
            new_head = self.portals[other_idx]

            # 移動蛇：直接從出口出現（跳過一般移動流程）
            self.snake.insert(0, new_head)
            if self.pending_growth:
                self.pending_growth -= 1
            else:
                self.snake.pop()

            return  # ✅ 傳送完直接結束 update（不再檢查碰撞）

        # 碰撞
        if new_head in self.obstacles:
            self.game_over = True; 
            self.save_score(self.player_name, len(self.snake), self.difficulty)
            return
        if new_head in self.snake and len(self.snake) > 2:
            idx = self.snake.index(new_head)
            self.snake = self.snake[idx:]
            self.save_score(self.player_name, len(self.snake), self.difficulty)
        
        if new_head in self.bombs:
            self.bombs.remove(new_head)

            self.flash_explosion()  # 💥 爆炸動畫

            # 扣掉尾巴
            self.snake = self.snake[:-BOMB_EFFECT] if len(self.snake) > BOMB_EFFECT else self.snake[:1]

        # 移動蛇
        self.snake.insert(0, new_head)
        if self.pending_growth:
            self.pending_growth -= 1
        else:
            self.snake.pop()

        # 食物
        if new_head in self.food:
            self.food.remove(new_head)
            self.pending_growth += 1
            self.snake.reverse()
            if len(self.snake) >= 2:
                hx, hy = self.snake[0]; nx, ny = self.snake[1]
                self.direction = (hx-nx, hy-ny)

        if new_head in self.confuses:
            self.confuses.remove(new_head)
            self.confuse_remaining = CONFUSE_DURATION


        # 加速道具
        if new_head in self.boosts:
            self.boosts.remove(new_head)
            self.boost_remaining = BOOST_DURATION
            self.fps = self.base_fps + BOOST_FPS_INC

        if new_head in self.portals:
            idx = self.portals.index(new_head)
            if idx % 2 == 0:
                other_idx = idx + 1
            else:
                other_idx = idx - 1
            new_head = self.portals[other_idx]

            # 移動蛇：直接從出口出現（跳過一般移動流程）
            self.snake.insert(0, new_head)
            if self.pending_growth:
                self.pending_growth -= 1
            else:
                self.snake.pop()
            return
        
        # 在 update 中處理 Boss 模式效果
        if BOSS_MODE:
            if self.age % (FPS_BASE * 10) == 0 and len(self.snake) > 1:
                self.snake.pop()

        if new_head in self.fake_food:
            self.fake_food.remove(new_head)
            penalty = random.randint(2, 5)
            self.snake = self.snake[:-penalty] if len(self.snake) > penalty else self.snake[:1]

        if new_head in self.invisible_obstacles:
            self.game_over = True
            self.save_score(self.player_name, len(self.snake), self.difficulty)
            return


    def save_score(self, name, score, level):
        filename = f"scores_level{level}.txt"
        scores = self.load_scores(level, full=True)  # ← 這裡要有縮排

        updated = False
        for i, (n, s) in enumerate(scores):
            if n == name:
                if score > s:
                    scores[i] = (name, score)
                updated = True
                break
        if not updated:
            scores.append((name, score))

        # 按照分數排序後覆寫檔案
        scores = sorted(scores, key=lambda x: x[1], reverse=True)
        with open(filename, "w", encoding="utf-8") as f:
            for n, s in scores:
                f.write(f"{n},{s}\n")

    def load_scores(self, level, full=False):
        filename = f"scores_level{level}.txt"
        scores = []
        try:
            with open(filename, "r", encoding="utf-8") as f:
                for line in f:
                    name, sc = line.strip().split(",")
                    scores.append((name, int(sc)))
        except FileNotFoundError:
            pass
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores if full else scores[:5]

    def show_leaderboard(self):
        scores = self.load_scores(self.difficulty)
        self.screen.fill(C_BG)
        title = self.font.render(f"Leaderboard - Level {self.difficulty}", True, C_TEXT)
        self.screen.blit(title, ((WINDOW_W - title.get_width()) // 2, 50))

        if not scores:
            no_data = self.font.render("No scores yet.", True, C_TEXT)
            self.screen.blit(no_data, ((WINDOW_W - no_data.get_width()) // 2, 100))
        else:
            for i, (name, score) in enumerate(scores):
                entry = self.font.render(f"{i+1}. {name} - {score}", True, C_TEXT)
                self.screen.blit(entry, (WINDOW_W//3, 120 + i * 30))

        msg = self.font.render("Press any key to quit", True, C_MENU)
        self.screen.blit(msg, ((WINDOW_W - msg.get_width()) // 2, WINDOW_H - 80))
        pygame.display.flip()

        waiting = True
        while waiting:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if e.type == pygame.KEYDOWN:
                    waiting = False


    # ────────────────────────────────────────────────
    # 畫面
    # ────────────────────────────────────────────────
    def render(self):
        self.screen.fill(C_BG)
        # 格線
        for x in range(GRID_W):
            for y in range(GRID_H):
                pygame.draw.rect(self.screen, C_GRID,
                                 pygame.Rect(x*CELL_SIZE, y*CELL_SIZE+SCOREBAR_H, CELL_SIZE, CELL_SIZE), 1)
        # 框線
        pygame.draw.rect(self.screen, C_BOUND, pygame.Rect(0,SCOREBAR_H,WINDOW_W,WINDOW_H-SCOREBAR_H),2)

        # 炸彈（深紅圓 + 黑色引線）
        for bx, by in self.bombs:
            center = (bx * CELL_SIZE + CELL_SIZE // 2, by * CELL_SIZE + SCOREBAR_H + CELL_SIZE // 2)

            # 圓形炸彈主體
            pygame.draw.circle(self.screen, C_BOMB, center, CELL_SIZE // 2 - 2)

            # 小引線（上方一小條）
            fuse_start = (center[0], center[1] - CELL_SIZE // 2 + 2)
            fuse_end = (center[0], center[1] - CELL_SIZE // 2 - 3)
            pygame.draw.line(self.screen, (0, 0, 0), fuse_start, fuse_end, 2)

        # 傳送門（每對一色 + 編號）
        for i in range(0, len(self.portals), 2):
            color = PORTAL_COLORS[(i//2) % len(PORTAL_COLORS)]
            label = self.small_font.render(str(i//2 + 1), True, color)

            for j in (0, 1):
                px, py = self.portals[i + j]
                center = (px * CELL_SIZE + CELL_SIZE // 2, py * CELL_SIZE + SCOREBAR_H + CELL_SIZE // 2)

                # 閃爍感 – 可選厚度切換
                thickness = 2 + (self.age // 5) % 2
                pygame.draw.circle(self.screen, color, center, CELL_SIZE // 2 - 1, thickness)

                # 編號放在門的右下角
                text_x = center[0] + CELL_SIZE // 2 - 5
                text_y = center[1] + CELL_SIZE // 2 - 5
                self.screen.blit(label, (text_x, text_y))


        # 障礙
        for ox, oy in self.obstacles:
            pygame.draw.rect(self.screen, C_OBST,
                             pygame.Rect(ox*CELL_SIZE, oy*CELL_SIZE+SCOREBAR_H, CELL_SIZE, CELL_SIZE))
        # 食物（蘋果造型）
        for fx, fy in self.food:
            # 畫紅色圓形作為蘋果果實
            center = (fx*CELL_SIZE + CELL_SIZE//2, fy*CELL_SIZE + SCOREBAR_H + CELL_SIZE//2)
            pygame.draw.circle(self.screen, C_FOOD, center, CELL_SIZE//2 - 2)

            # 畫小綠葉（上方小矩形）
            leaf_rect = pygame.Rect(center[0] - 2, center[1] - CELL_SIZE//2 + 2, 4, 4)
            pygame.draw.rect(self.screen, (0, 200, 0), leaf_rect)

        # Boost（閃電造型）
        for bx, by in self.boosts:
            x0 = bx * CELL_SIZE
            y0 = by * CELL_SIZE + SCOREBAR_H

            points = [
                (x0 + CELL_SIZE//2 - 2, y0 + 2),          # 上尖
                (x0 + CELL_SIZE//2 + 1, y0 + CELL_SIZE//2 - 4),
                (x0 + CELL_SIZE//2 - 3, y0 + CELL_SIZE//2 - 4),
                (x0 + CELL_SIZE//2 + 2, y0 + CELL_SIZE - 4),  # 下尖
                (x0 + CELL_SIZE//2 - 1, y0 + CELL_SIZE//2 + 2),
                (x0 + CELL_SIZE//2 + 3, y0 + CELL_SIZE//2 + 2)
            ]

            pygame.draw.polygon(self.screen, C_BOOST, points)

        # 🌀 迷惑道具 – 模擬螺旋圖樣
        for cx, cy in self.confuses:
            center_x = cx * CELL_SIZE + CELL_SIZE // 2
            center_y = cy * CELL_SIZE + SCOREBAR_H + CELL_SIZE // 2
            for i in range(5):
                angle = i * 72
                radius = 2 + i
                offset_x = int(radius * (i / 5) * (-1) ** i)
                offset_y = int(radius * ((4 - i) / 5) * (-1) ** (i + 1))
                pygame.draw.circle(self.screen, C_CONFUSE,
                                    (center_x + offset_x, center_y + offset_y), 2)

        # 蛇
        snake_color = C_SNAKE_CONFUSE if self.confuse_remaining > 0 else C_SNAKE
        for i, (sx, sy) in enumerate(self.snake):
            rect = pygame.Rect(sx*CELL_SIZE, sy*CELL_SIZE+SCOREBAR_H, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(self.screen, snake_color, rect)
            if i==0:
                eye = CELL_SIZE//5
                pygame.draw.circle(self.screen, C_BG, (rect.x+CELL_SIZE//3, rect.y+CELL_SIZE//3), eye)
                pygame.draw.circle(self.screen, C_BG, (rect.x+2*CELL_SIZE//3, rect.y+CELL_SIZE//3), eye)

        # Info
        info = f"Len {len(self.snake)}  FPS {self.fps}  D{self.difficulty}"
        if self.boost_remaining > 0: info += " BOOST"
        self.screen.blit(self.font.render(info, True, C_TEXT), (10, 10))

        if self.game_over:
            msg = self.font.render("GAME OVER – Play again? (Y/N)", True, C_GAMEOVER)
            self.screen.blit(msg, ((WINDOW_W - msg.get_width()) // 2, WINDOW_H // 2))
            pygame.display.flip()

            waiting = True
            while waiting:
                for e in pygame.event.get():
                    if e.type == pygame.QUIT:
                        pygame.quit(); sys.exit()
                    if e.type == pygame.KEYDOWN:
                        if e.key in (pygame.K_y, pygame.K_y):
                            self.reset()
                            waiting = False
                        elif e.key in (pygame.K_n, pygame.K_n):
                            self.show_leaderboard()
                            pygame.quit(); sys.exit()
        pygame.display.flip()  # 或者 pygame.display.update()


    # ────────────────────────────────────────────────
    # 工具：隨機生成 / 移動道具
    # ────────────────────────────────────────────────
    def spawn_food(self):
        for _ in range(1000):
            p = (random.randint(0,GRID_W-1), random.randint(0,GRID_H-1))
            if p not in self.snake and p not in self.obstacles and p not in self.food:
                self.food.add(p); return

    def spawn_boost(self):
        for _ in range(1000):
            p = (random.randint(0,GRID_W-1), random.randint(0,GRID_H-1))
            if p not in self.snake and p not in self.obstacles and p not in self.food and p not in self.boosts:
                self.boosts.add(p); return
            
    def spawn_bomb(self):
        for _ in range(1000):
            p = (random.randint(0, GRID_W-1), random.randint(0, GRID_H-1))
            if p not in self.snake and p not in self.obstacles and p not in self.food and p not in self.boosts and p not in self.bombs:
                self.bombs.add(p)
                return
    
    def spawn_confuse(self):
        for _ in range(1000):
            p = (random.randint(0, GRID_W-1), random.randint(0, GRID_H-1))
            if p not in self.snake and p not in self.obstacles and p not in self.food and p not in self.boosts and p not in self.bombs and p not in self.confuses:
                self.confuses.add(p)
                return
    
    def spawn_portals(self):
        forbidden = set(self.snake) | self.obstacles | self.food | self.boosts | self.bombs | self.confuses
        all_positions = {(x, y) for x in range(GRID_W) for y in range(GRID_H)}
        candidates = list(all_positions - forbidden)

        total_needed = self.num_portal_pairs * 2
        if len(candidates) >= total_needed:
            self.portals = random.sample(candidates, total_needed)


    def random_edge_position(self):
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":
            return random.randint(0, GRID_W-1), 0
        elif side == "bottom":
            return random.randint(0, GRID_W-1), GRID_H-1
        elif side == "left":
            return 0, random.randint(0, GRID_H-1)
        else:
            return GRID_W-1, random.randint(0, GRID_H-1)

    def relocate_obstacles(self):
        new_obs = set()
        attempts = 0
        while len(new_obs) < OBSTACLE_COUNT and attempts < OBSTACLE_COUNT * 100:
            p = (random.randint(0, GRID_W-1), random.randint(0, GRID_H-1))
            if p not in self.snake and p not in self.food and p not in self.boosts:
                new_obs.add(p)
            attempts += 1
        self.obstacles = new_obs

    def relocate_foods(self):
        new_foods = set()
        for _ in range(len(self.food)):
            for _ in range(1000):
                p = (random.randint(0, GRID_W-1), random.randint(0, GRID_H-1))
                if p not in self.snake and p not in self.obstacles and p not in new_foods:
                    new_foods.add(p)
                    break
        self.food = new_foods

# ────────────────────────────────────────────────────────────────────
# 執行
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    game = SnakeGame()
    game.run()
