"""
Space Invaders — Nels & Dad Edition (v2, merged)
Dual weapons: lasers (unlimited) and rockets (AoE, cooldown)
Works with keyboard (laptop dev) OR arcade stick + 2 buttons (cabinet deploy)

"""

import pygame
import random
import math
import os

# --- CONFIG ---------------------------------------------------------------
SCREEN_W, SCREEN_H = 1920, 1080
FPS = 120

BLACK  = (0, 0, 0)
WHITE  = (255, 255, 255)
GREEN  = (0, 255, 0)
RED    = (255, 60, 60)
YELLOW = (255, 220, 0)
CYAN   = (0, 255, 255)
PURPLE = (200, 0, 200)

PLAYER_SPEED = 9
LASER_SPEED = 7
LASER_COOLDOWN_MS = 600
ROCKET_SPEED = 9
ROCKET_COOLDOWN_MS = 2000
ROCKET_BLAST_RADIUS = 150
ENEMY_BULLET_SPEED = 7
ENEMY_COLS = 25
ENEMY_ROWS = 8
BUNKER_COUNT = 10

ENEMY_STEP_DOWN = 20
WAVE_STEP_BONUS = 3

ENEMY_SPEED_BASE = 1.0
ENEMY_SPEED_MAX = 5.0
WAVE_SPEED_BONUS = 0.4
ENEMY_SHOOT_BASE_MS = 1200
ENEMY_SHOOT_MIN_MS = 250
WAVE_SHOOT_BONUS_MS = 100

JOY_DEADZONE = 0.3
JOY_BUTTON_LASER = 0
JOY_BUTTON_ROCKET = 1
JOY_BUTTON_PAUSE = 2

# --- ENTITY BASE (merged pattern #1) --------------------------------------
class Entity:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.alive = True
    def rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)

# --- INPUT LAYER ----------------------------------------------------------
class Input:
    def __init__(self):
        pygame.joystick.init()
        self.joystick = None
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"Using joystick: {self.joystick.get_name()}")
        else:
            print("Using keyboard: Arrows + Z (laser) + X (rocket)")

    def left(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: return True
        if self.joystick and self.joystick.get_axis(0) < -JOY_DEADZONE: return True
        return False

    def right(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: return True
        if self.joystick and self.joystick.get_axis(0) > JOY_DEADZONE: return True
        return False

    def laser_pressed(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_z, pygame.K_SPACE):
            return True
        if event.type == pygame.JOYBUTTONDOWN and event.button == JOY_BUTTON_LASER:
            return True
        return False

    def rocket_pressed(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_x, pygame.K_LCTRL):
            return True
        if event.type == pygame.JOYBUTTONDOWN and event.button == JOY_BUTTON_ROCKET:
            return True
        return False

# --- ENTITIES -------------------------------------------------------------
class Player(Entity):
    def __init__(self):
        super().__init__(SCREEN_W // 2 - 20, SCREEN_H - 60, 40, 20)
        self.lives = 3
    def update(self, inp):
        if inp.left():  self.x = max(0, self.x - PLAYER_SPEED)
        if inp.right(): self.x = min(SCREEN_W - self.w, self.x + PLAYER_SPEED)
    def draw(self, screen):
        pygame.draw.rect(screen, GREEN, self.rect())
        pygame.draw.rect(screen, GREEN, (self.x + self.w//2 - 3, self.y - 8, 6, 8))

class Laser(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 3, 12)
        self.pierce = random.randint(1, 3)
    def update(self):
        self.y -= LASER_SPEED
        if self.y < 0: self.alive = False
    def draw(self, screen):
        pygame.draw.rect(screen, RED, self.rect())

class Rocket(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 6, 16)
    def update(self):
        self.y -= ROCKET_SPEED
        if self.y < 0: self.alive = False
    def draw(self, screen):
        pygame.draw.rect(screen, YELLOW, self.rect())
        pygame.draw.polygon(screen, RED, [
            (self.x, self.y + self.h),
            (self.x + self.w, self.y + self.h),
            (self.x + self.w//2, self.y + self.h + 8),
        ])

class Explosion(Entity):
    def __init__(self, x, y, max_radius=None):
        super().__init__(x, y, 0, 0)
        self.max_radius = max_radius if max_radius is not None else ROCKET_BLAST_RADIUS
        self.radius = min(10, self.max_radius)
    def update(self):
        self.radius += 4
        if self.radius >= self.max_radius:
            self.alive = False
    def hits(self, rect):
        cx, cy = rect.centerx, rect.centery
        return math.hypot(cx - self.x, cy - self.y) < self.radius
    def draw(self, screen):
        pygame.draw.circle(screen, YELLOW, (self.x, self.y), self.radius, 3)
        pygame.draw.circle(screen, RED, (self.x, self.y), self.radius - 6, 2)

class Enemy(Entity):
    def __init__(self, x, y, row, col, tier):
        super().__init__(x, y, 30, 20)
        self.row, self.col, self.tier = row, col, tier
        self.points = [10, 20, 40][tier]
        self.color = [GREEN, CYAN, PURPLE][tier]
        self._jfx = random.uniform(0.1, 0.4)
        self._jfy = random.uniform(0.08, 0.3)
        self._jpx = random.uniform(0, math.tau)
        self._jpy = random.uniform(0, math.tau)
    def draw(self, screen, frame=0):
        a = (frame // 30) % 2
        jx = int(math.sin(frame * self._jfx + self._jpx) * 2)
        jy = int(math.cos(frame * self._jfy + self._jpy) * 1)
        x, y = self.x + jx, self.y + jy
        if self.tier == 0:
            self._draw_crab(screen, a, x, y)
        elif self.tier == 1:
            self._draw_squid(screen, a, x, y)
        else:
            self._draw_jellyfish(screen, a, x, y)
    def _draw_crab(self, screen, a, x, y):
        pygame.draw.rect(screen, self.color, (x, y, self.w, self.h))
        pygame.draw.rect(screen, BLACK, (x + 5, y + 5, 5, 5))
        pygame.draw.rect(screen, BLACK, (x + 20, y + 5, 5, 5))
        arm_y = y + 3 + a * 3
        pygame.draw.rect(screen, self.color, (x - 7, arm_y, 7, 4))
        pygame.draw.rect(screen, self.color, (x + self.w, arm_y, 7, 4))
        pygame.draw.rect(screen, self.color, (x + 4, y + self.h, 4, 3 + a))
        pygame.draw.rect(screen, self.color, (x + self.w - 8, y + self.h, 4, 3 + a))
    def _draw_squid(self, screen, a, x, y):
        pygame.draw.rect(screen, self.color, (x + 3, y, self.w - 6, self.h))
        pygame.draw.rect(screen, BLACK, (x + 8, y + 5, 4, 4))
        pygame.draw.rect(screen, BLACK, (x + 18, y + 5, 4, 4))
        pygame.draw.rect(screen, self.color, (x + 7, y - 4 - a, 3, 4 + a))
        pygame.draw.rect(screen, self.color, (x + 20, y - 4 - a, 3, 4 + a))
        for i in range(3):
            pygame.draw.rect(screen, self.color, (x + 4 + i * 9, y + self.h, 3, 4 + a * (i % 2)))
    def _draw_jellyfish(self, screen, a, x, y):
        pygame.draw.ellipse(screen, self.color, (x, y, self.w, self.h))
        pygame.draw.rect(screen, BLACK, (x + 6, y + 5, 4, 4))
        pygame.draw.rect(screen, BLACK, (x + 20, y + 5, 4, 4))
        for i in range(4):
            pygame.draw.rect(screen, self.color, (x + 3 + i * 7, y + self.h - 2, 2, 4 + a * (i % 2) * 2))

class EnemyBullet(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 3, 10)
        self._dot_offsets = [(random.randint(-6, 6), random.randint(-6, 6)) for _ in range(5)]
    def update(self):
        self.y += ENEMY_BULLET_SPEED
        if self.y > SCREEN_H: self.alive = False
    def draw(self, screen):
        cx, cy = self.x + self.w // 2, self.y + self.h // 2
        for dx, dy in self._dot_offsets:
            pygame.draw.circle(screen, RED, (cx + dx, cy + dy), 1)
        pygame.draw.rect(screen, RED, self.rect())

class Bunker:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.block = 6
        self.cols, self.rows = 10, 6
        self.grid = [[True]*self.cols for _ in range(self.rows)]
        for r in range(self.rows-2, self.rows):
            for c in range(3, 7):
                self.grid[r][c] = False
    def block_rects(self):
        rects = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c]:
                    rects.append((r, c, pygame.Rect(
                        self.x + c*self.block, self.y + r*self.block,
                        self.block, self.block)))
        return rects
    def hit(self, rect):
        for r, c, br in self.block_rects():
            if br.colliderect(rect):
                self.grid[r][c] = False
                return True
        return False
    def hit_explosion(self, exp):
        damaged = False
        for r, c, br in self.block_rects():
            if exp.hits(br):
                self.grid[r][c] = False
                damaged = True
        return damaged
    def draw(self, screen):
        for _, _, br in self.block_rects():
            pygame.draw.rect(screen, GREEN, br)

UFO_STYLES = [
    {"color": RED,    "speed": 3, "points": [50, 100, 150, 300]},
    {"color": PURPLE, "speed": 5, "points": [200, 300, 400]},
    {"color": YELLOW, "speed": 2, "points": [500, 750, 1000]},
    {"color": CYAN,   "speed": 6, "points": [100, 100, 100, 100, 500]},
]

class UFO(Entity):
    def __init__(self):
        super().__init__(-50, 40, 50, 16)
        self.style = UFO_STYLES[0]
        self.reset()
    def reset(self):
        self.alive = False
        self.next_spawn = pygame.time.get_ticks() + random.randint(6000, 12000)
        self.direction = 1
    def maybe_spawn(self):
        if not self.alive and pygame.time.get_ticks() > self.next_spawn:
            self.alive = True
            self.style = random.choice(UFO_STYLES)
            self.direction = random.choice([-1, 1])
            self.x = -self.w if self.direction == 1 else SCREEN_W
            self.y = random.randint(30, 80)
    def update(self):
        if not self.alive: return
        self.x += self.style["speed"] * self.direction
        if self.x < -self.w or self.x > SCREEN_W:
            self.alive = False
            self.next_spawn = pygame.time.get_ticks() + random.randint(6000, 12000)
    def draw(self, screen):
        if not self.alive: return
        color = self.style["color"]
        pygame.draw.ellipse(screen, color, self.rect())
        pygame.draw.rect(screen, WHITE, (self.x + 10, self.y + 4, self.w - 20, 4))
        pygame.draw.circle(screen, WHITE, (int(self.x + self.w // 2), self.y + 3), 4)
    def points(self):
        return random.choice(self.style["points"])

# --- WAVE -----------------------------------------------------------------
def spawn_wave(wave_num):
    enemies = []
    margin = SCREEN_W // 10
    col_spacing = (SCREEN_W - 2 * margin) // ENEMY_COLS
    start_x = margin
    start_y = 80 + min(wave_num * 10, 120)
    for r in range(ENEMY_ROWS):
        for c in range(ENEMY_COLS):
            x = start_x + c * col_spacing
            y = start_y + r * 35
            tier = random.choices([0, 1, 2], weights=[5, 3, 2])[0]
            enemies.append(Enemy(x, y, r, c, tier))
    return enemies

# --- DIFFICULTY SCALING (merged pattern #3) -------------------------------
def enemy_speed(enemies, wave):
    alive = sum(1 for e in enemies if e.alive)
    total = len(enemies) if enemies else 1
    ratio = alive / total if total else 1
    speed = ENEMY_SPEED_MAX - (ENEMY_SPEED_MAX - ENEMY_SPEED_BASE) * ratio
    speed += WAVE_SPEED_BONUS * (wave - 1)
    return min(speed, ENEMY_SPEED_MAX)

def shoot_interval(enemies, wave):
    alive = sum(1 for e in enemies if e.alive)
    total = len(enemies) if enemies else 1
    ratio = alive / total if total else 1
    interval = ENEMY_SHOOT_BASE_MS * ratio
    interval -= WAVE_SHOOT_BONUS_MS * (wave - 1)
    return max(ENEMY_SHOOT_MIN_MS, interval)

# --- FRONT-ROW SHOOTERS (merged pattern #2) -------------------------------
def pick_shooter(enemies):
    columns = {}
    for e in enemies:
        if not e.alive: continue
        if e.col not in columns or e.y > columns[e.col].y:
            columns[e.col] = e
    shooters = list(columns.values())
    return random.choice(shooters) if shooters else None

# --- MAIN -----------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Space Invaders — Nels & Dad Edition")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 32)
    big_font = pygame.font.Font(None, 72)
    inp = Input()

    def new_game():
        return {
            "player": Player(),
            "lasers": [], "rockets": [], "explosions": [],
            "enemies": spawn_wave(1),
            "enemy_bullets": [],
            "bunkers": [Bunker(SCREEN_W // (BUNKER_COUNT + 1) * (i + 1) - 30, SCREEN_H - 140) for i in range(BUNKER_COUNT)],
            "ufos": [UFO() for _ in range(3)],
            "score": 0, "wave": 1,
            "enemy_dir": 1,
            "last_rocket": -ROCKET_COOLDOWN_MS,
            "last_laser": -LASER_COOLDOWN_MS,
            "enemy_shoot_timer": 0,
            "game_over": False, "paused": False,
            "frame": 0,
        }

    state = new_game()
    running = True

    while running:
        dt = clock.tick(FPS)
        now = pygame.time.get_ticks()
        state["frame"] += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_p) or \
               (event.type == pygame.JOYBUTTONDOWN and event.button == JOY_BUTTON_PAUSE):
                state["paused"] = not state["paused"]
            if state["game_over"]:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    state = new_game()
                if event.type == pygame.JOYBUTTONDOWN:
                    state = new_game()
                continue
            if state["paused"]: continue
            if inp.laser_pressed(event):
                if now - state["last_laser"] >= LASER_COOLDOWN_MS:
                    p = state["player"]
                    state["lasers"].append(Laser(p.x + p.w//2 - 1, p.y - 12))
                    state["last_laser"] = now
            if inp.rocket_pressed(event):
                if now - state["last_rocket"] >= ROCKET_COOLDOWN_MS:
                    p = state["player"]
                    state["rockets"].append(Rocket(p.x + p.w//2 - 3, p.y - 16))
                    state["last_rocket"] = now

        if state["game_over"]:
            draw_game_over(screen, font, big_font, state["score"])
            pygame.display.flip()
            continue
        if state["paused"]:
            draw_paused(screen, font)
            pygame.display.flip()
            continue

        # Update
        state["player"].update(inp)
        for l in state["lasers"]: l.update()
        for r in state["rockets"]: r.update()
        for e in state["explosions"]: e.update()
        for b in state["enemy_bullets"]: b.update()
        for ufo in state["ufos"]: ufo.maybe_spawn(); ufo.update()

        alive_enemies = [e for e in state["enemies"] if e.alive]
        if alive_enemies:
            leftmost = min(e.x for e in alive_enemies)
            rightmost = max(e.x + e.w for e in alive_enemies)
            speed = enemy_speed(state["enemies"], state["wave"]) * state["enemy_dir"]
            hit_edge = (state["enemy_dir"] == 1 and rightmost + speed >= SCREEN_W) or \
                       (state["enemy_dir"] == -1 and leftmost + speed <= 0)
            if hit_edge:
                state["enemy_dir"] *= -1
                step = ENEMY_STEP_DOWN + WAVE_STEP_BONUS * (state["wave"] - 1)
                for e in alive_enemies: e.y += step
            else:
                for e in alive_enemies: e.x += speed

        state["enemy_shoot_timer"] += dt
        if state["enemy_shoot_timer"] > shoot_interval(state["enemies"], state["wave"]):
            state["enemy_shoot_timer"] = 0
            shooter = pick_shooter(state["enemies"])
            if shooter:
                state["enemy_bullets"].append(
                    EnemyBullet(shooter.x + shooter.w//2, shooter.y + shooter.h))

        # Collisions
        for l in state["lasers"]:
            if not l.alive: continue
            for e in state["enemies"]:
                if e.alive and l.rect().colliderect(e.rect()):
                    e.alive = False
                    state["score"] += e.points
                    l.pierce -= 1
                    if l.pierce <= 0:
                        l.alive = False
                    break
            for b in state["bunkers"]:
                if l.alive and b.hit(l.rect()): l.alive = False
            for ufo in state["ufos"]:
                if l.alive and ufo.alive and l.rect().colliderect(ufo.rect()):
                    l.alive = False; ufo.alive = False
                    ufo.next_spawn = now + random.randint(6000, 12000)
                    state["score"] += ufo.points()

        for r in state["rockets"]:
            if not r.alive: continue
            exploded = False
            for e in state["enemies"]:
                if e.alive and r.rect().colliderect(e.rect()):
                    exploded = True; break
            if not exploded:
                for b in state["bunkers"]:
                    for _, _, br in b.block_rects():
                        if r.rect().colliderect(br):
                            exploded = True; break
                    if exploded: break
            if r.y < 20: exploded = True
            if exploded:
                r.alive = False
                state["explosions"].append(Explosion(r.x + r.w//2, r.y + r.h//2))

        for exp in state["explosions"]:
            for e in state["enemies"]:
                if e.alive and exp.hits(e.rect()):
                    e.alive = False
                    state["score"] += e.points
            for b in state["bunkers"]: b.hit_explosion(exp)
            for ufo in state["ufos"]:
                if ufo.alive and exp.hits(ufo.rect()):
                    ufo.alive = False
                    state["score"] += ufo.points()

        for b in state["enemy_bullets"]:
            if not b.alive: continue
            if b.rect().colliderect(state["player"].rect()):
                b.alive = False
                state["player"].lives -= 1
                state["explosions"].append(Explosion(b.x + b.w // 2, b.y, 35))
                if state["player"].lives <= 0:
                    state["game_over"] = True
            for bunker in state["bunkers"]:
                if b.alive and bunker.hit(b.rect()):
                    b.alive = False

        for e in state["enemies"]:
            if e.alive and e.y + e.h >= state["player"].y:
                state["game_over"] = True

        state["lasers"]        = [x for x in state["lasers"]        if x.alive]
        state["rockets"]       = [x for x in state["rockets"]       if x.alive]
        state["explosions"]    = [x for x in state["explosions"]    if x.alive]
        state["enemy_bullets"] = [x for x in state["enemy_bullets"] if x.alive]

        if not any(e.alive for e in state["enemies"]):
            state["wave"] += 1
            state["enemies"] = spawn_wave(state["wave"])

        # Draw
        screen.fill(BLACK)
        random.seed(42)
        for _ in range(50):
            pygame.draw.circle(screen, WHITE,
                (random.randint(0, SCREEN_W), random.randint(0, SCREEN_H)), 1)
        random.seed()

        state["player"].draw(screen)
        for l in state["lasers"]:         l.draw(screen)
        for r in state["rockets"]:        r.draw(screen)
        for exp in state["explosions"]:   exp.draw(screen)
        for b in state["enemy_bullets"]:  b.draw(screen)
        for bunker in state["bunkers"]:   bunker.draw(screen)
        for e in state["enemies"]:
            if e.alive: e.draw(screen, state["frame"])
        for ufo in state["ufos"]: ufo.draw(screen)

        score_surf = font.render(f"SCORE {state['score']:06d}", True, WHITE)
        screen.blit(score_surf, (20, 10))
        wave_surf = font.render(f"WAVE {state['wave']}", True, WHITE)
        screen.blit(wave_surf, (SCREEN_W//2 - 40, 10))
        lives_surf = font.render(f"LIVES {state['player'].lives}", True, WHITE)
        screen.blit(lives_surf, (SCREEN_W - 140, 10))

        cd_ready = now - state["last_rocket"] >= ROCKET_COOLDOWN_MS
        cd_color = YELLOW if cd_ready else RED
        pygame.draw.rect(screen, cd_color, (20, SCREEN_H - 30, 100, 10), 0 if cd_ready else 2)
        if not cd_ready:
            frac = (now - state["last_rocket"]) / ROCKET_COOLDOWN_MS
            pygame.draw.rect(screen, cd_color, (20, SCREEN_H - 30, int(100*frac), 10))
        screen.blit(font.render("ROCKET", True, WHITE), (130, SCREEN_H - 35))

        pygame.display.flip()

    pygame.quit()


def draw_game_over(screen, font, big_font, score):
    screen.fill(BLACK)
    go = big_font.render("GAME OVER", True, RED)
    screen.blit(go, (SCREEN_W//2 - go.get_width()//2, 200))
    sc = font.render(f"Final Score: {score}", True, WHITE)
    screen.blit(sc, (SCREEN_W//2 - sc.get_width()//2, 300))
    hint = font.render("Press Enter (or any button) to restart", True, WHITE)
    screen.blit(hint, (SCREEN_W//2 - hint.get_width()//2, 360))


def draw_paused(screen, font):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H))
    overlay.set_alpha(180)
    overlay.fill(BLACK)
    screen.blit(overlay, (0, 0))
    big_font = pygame.font.Font(None, 100) 
    paused_msg1 = big_font.render("GAME PAUSED", True, PINK)
    paused_msg2 = font.render("Press the Dude button again to resume!", True, GREEN)
    screen.blit(msg, (SCREEN_W//2 - msg.get_width()//2, SCREEN_H//2))


if __name__ == "__main__":
    main()
