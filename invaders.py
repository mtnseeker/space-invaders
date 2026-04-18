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
FPS = 60

BLACK  = (0, 0, 0)
WHITE  = (255, 255, 255)
GREEN  = (0, 255, 0)
RED    = (255, 60, 60)
YELLOW = (255, 220, 0)
CYAN   = (0, 255, 255)
PURPLE = (200, 0, 200)

PLAYER_SPEED = 5
LASER_SPEED = 10
ROCKET_SPEED = 7
ROCKET_COOLDOWN_MS = 2000
ROCKET_BLAST_RADIUS = 60
ENEMY_BULLET_SPEED = 4
ENEMY_STEP_DOWN = 20

ENEMY_SPEED_BASE = 1.0
ENEMY_SPEED_MAX = 5.0
WAVE_SPEED_BONUS = 0.4
ENEMY_SHOOT_BASE_MS = 1200
ENEMY_SHOOT_MIN_MS = 250
WAVE_SHOOT_BONUS_MS = 100

JOY_DEADZONE = 0.3
JOY_BUTTON_LASER = 0
JOY_BUTTON_ROCKET = 1

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
    def update(self):
        self.y -= LASER_SPEED
        if self.y < 0: self.alive = False
    def draw(self, screen):
        pygame.draw.rect(screen, CYAN, self.rect())

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
    def __init__(self, x, y):
        super().__init__(x, y, 0, 0)
        self.radius = 10
        self.max_radius = ROCKET_BLAST_RADIUS
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
    def draw(self, screen, frame=0):
        offset = 2 if (frame // 30) % 2 == 0 else 0
        pygame.draw.rect(screen, self.color, self.rect())
        pygame.draw.rect(screen, BLACK, (self.x + 6, self.y + 6, 4, 4))
        pygame.draw.rect(screen, BLACK, (self.x + 20, self.y + 6, 4, 4))
        pygame.draw.rect(screen, self.color, (self.x - 2, self.y + self.h, 4, 3 + offset))
        pygame.draw.rect(screen, self.color, (self.x + self.w - 2, self.y + self.h, 4, 3 + offset))

class EnemyBullet(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 3, 10)
    def update(self):
        self.y += ENEMY_BULLET_SPEED
        if self.y > SCREEN_H: self.alive = False
    def draw(self, screen):
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

class UFO(Entity):
    def __init__(self):
        super().__init__(-50, 40, 50, 16)
        self.reset()
    def reset(self):
        self.alive = False
        self.next_spawn = pygame.time.get_ticks() + random.randint(15000, 25000)
        self.direction = 1
    def maybe_spawn(self):
        if not self.alive and pygame.time.get_ticks() > self.next_spawn:
            self.alive = True
            self.direction = random.choice([-1, 1])
            self.x = -self.w if self.direction == 1 else SCREEN_W
            self.y = 40
    def update(self):
        if not self.alive: return
        self.x += 3 * self.direction
        if self.x < -self.w or self.x > SCREEN_W:
            self.alive = False
            self.next_spawn = pygame.time.get_ticks() + random.randint(15000, 25000)
    def draw(self, screen):
        if not self.alive: return
        pygame.draw.ellipse(screen, RED, self.rect())
        pygame.draw.rect(screen, YELLOW, (self.x + 10, self.y + 4, self.w - 20, 4))

# --- WAVE -----------------------------------------------------------------
def spawn_wave(wave_num):
    enemies = []
    rows, cols = 5, 10
    margin = SCREEN_W // 10
    col_spacing = (SCREEN_W - 2 * margin) // cols
    start_x = margin
    start_y = 80 + min(wave_num * 10, 120)
    for r in range(rows):
        tier = 2 if r == 0 else (1 if r < 3 else 0)
        for c in range(cols):
            x = start_x + c * col_spacing
            y = start_y + r * 35
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
            "bunkers": [Bunker(SCREEN_W // 5 * (i + 1) - 30, SCREEN_H - 140) for i in range(4)],
            "ufo": UFO(),
            "score": 0, "wave": 1,
            "enemy_dir": 1,
            "last_rocket": -ROCKET_COOLDOWN_MS,
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
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                state["paused"] = not state["paused"]
            if state["game_over"]:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    state = new_game()
                if event.type == pygame.JOYBUTTONDOWN:
                    state = new_game()
                continue
            if state["paused"]: continue
            if inp.laser_pressed(event):
                p = state["player"]
                state["lasers"].append(Laser(p.x + p.w//2 - 1, p.y - 12))
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
        state["ufo"].maybe_spawn()
        state["ufo"].update()

        alive_enemies = [e for e in state["enemies"] if e.alive]
        if alive_enemies:
            leftmost = min(e.x for e in alive_enemies)
            rightmost = max(e.x + e.w for e in alive_enemies)
            speed = enemy_speed(state["enemies"], state["wave"]) * state["enemy_dir"]
            hit_edge = (state["enemy_dir"] == 1 and rightmost + speed >= SCREEN_W) or \
                       (state["enemy_dir"] == -1 and leftmost + speed <= 0)
            if hit_edge:
                state["enemy_dir"] *= -1
                for e in alive_enemies: e.y += ENEMY_STEP_DOWN
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
                    e.alive = False; l.alive = False
                    state["score"] += e.points
                    break
            for b in state["bunkers"]:
                if l.alive and b.hit(l.rect()): l.alive = False
            if l.alive and state["ufo"].alive and l.rect().colliderect(state["ufo"].rect()):
                l.alive = False; state["ufo"].alive = False
                state["ufo"].next_spawn = now + random.randint(15000, 25000)
                state["score"] += random.choice([50, 100, 150, 300])

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
            if state["ufo"].alive and exp.hits(state["ufo"].rect()):
                state["ufo"].alive = False
                state["score"] += 150

        for b in state["enemy_bullets"]:
            if not b.alive: continue
            if b.rect().colliderect(state["player"].rect()):
                b.alive = False
                state["player"].lives -= 1
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
        state["ufo"].draw(screen)

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
    msg = font.render("PAUSED — press P to resume", True, YELLOW)
    screen.blit(msg, (SCREEN_W//2 - msg.get_width()//2, SCREEN_H//2))


if __name__ == "__main__":
    main()
