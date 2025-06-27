import pygame
import sys
import math
import time

pygame.init()

WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Racing Game")

FPS = 60
clock = pygame.time.Clock()

WHITE = (255, 255, 255)
YELLOW = (255, 215, 0)
BLACK = (0, 0, 0)
GRAY = (130, 130, 130)
DARK_GRAY = (50, 50, 50)
GREEN = (30, 130, 30)

font_big = pygame.font.SysFont("Arial Black", 72)
font_medium = pygame.font.SysFont("Arial", 40)

menu_bg = pygame.image.load("menu_background.png").convert()
menu_bg = pygame.transform.scale(menu_bg, (WIDTH, HEIGHT))
track_bg = pygame.image.load("grass_background.png").convert()
track_bg = pygame.transform.scale(track_bg, (WIDTH, HEIGHT))
car_img_orig = pygame.image.load("car_sprite.png").convert_alpha()
car_img_orig = pygame.transform.scale(car_img_orig, (60, 40))

class Track:
    def __init__(self, type_id):
        self.type_id = type_id
        self.center = (WIDTH // 2, HEIGHT // 2)
        self.road_width = 120
        self.laps_required = 3
        self.finish_line_thickness = 8

        if type_id == 1:
            self.outer_radius = 300
            self.inner_radius = self.outer_radius - self.road_width
            self.finish_line = pygame.Rect(
                self.center[0] - self.finish_line_thickness // 2,
                self.center[1] - self.outer_radius,
                self.finish_line_thickness,
                self.road_width
            )
            self.start_pos = (self.center[0], self.center[1] + (self.inner_radius + self.outer_radius) // 2)

        elif type_id == 2:
            self.rx_outer = 350
            self.ry_outer = 220
            self.rx_inner = self.rx_outer - self.road_width
            self.ry_inner = self.ry_outer - self.road_width
            self.finish_line = pygame.Rect(
                self.center[0] - self.finish_line_thickness // 2,
                self.center[1] - self.ry_outer,
                self.finish_line_thickness,
                self.road_width
            )
            self.start_pos = (self.center[0], self.center[1] + (self.ry_inner + self.ry_outer) // 2)

        elif type_id == 3:
            self.outer_poly = [
                (300, 250), (900, 250), (950, 300), (950, 500),
                (900, 550), (300, 550), (250, 500), (250, 300)
            ]
            offset = 100
            self.inner_poly = [
                (300 + offset, 250 + offset), (900 - offset, 250 + offset),
                (900 - offset, 550 - offset), (300 + offset, 550 - offset)
            ]
            self.finish_line = pygame.Rect(590, 250, self.finish_line_thickness, self.road_width)
            self.start_pos = (600, 500)

    def draw(self, surface):
        surface.blit(track_bg, (0, 0))

        if self.type_id == 1:
            pygame.draw.circle(surface, DARK_GRAY, self.center, self.outer_radius)
            pygame.draw.circle(surface, GREEN, self.center, self.inner_radius)
            pygame.draw.rect(surface, WHITE, self.finish_line)

        elif self.type_id == 2:
            pygame.draw.ellipse(surface, DARK_GRAY,
                                [self.center[0] - self.rx_outer, self.center[1] - self.ry_outer,
                                 2 * self.rx_outer, 2 * self.ry_outer])
            pygame.draw.ellipse(surface, GREEN,
                                [self.center[0] - self.rx_inner, self.center[1] - self.ry_inner,
                                 2 * self.rx_inner, 2 * self.ry_inner])
            pygame.draw.rect(surface, WHITE, self.finish_line)

        elif self.type_id == 3:
            pygame.draw.polygon(surface, DARK_GRAY, self.outer_poly)
            pygame.draw.polygon(surface, GREEN, self.inner_poly)
            pygame.draw.rect(surface, WHITE, self.finish_line)

    def is_on_road(self, car_rect):
        cx, cy = car_rect.center

        if self.type_id == 1:
            dist = math.hypot(cx - self.center[0], cy - self.center[1])
            return self.inner_radius < dist < self.outer_radius

        elif self.type_id == 2:
            outer_val = ((cx - self.center[0]) ** 2) / (self.rx_outer ** 2) + ((cy - self.center[1]) ** 2) / (self.ry_outer ** 2)
            inner_val = ((cx - self.center[0]) ** 2) / (self.rx_inner ** 2) + ((cy - self.center[1]) ** 2) / (self.ry_inner ** 2)
            return inner_val >= 1 and outer_val <= 1

        elif self.type_id == 3:
            return point_in_polygon(cx, cy, self.outer_poly) and not point_in_polygon(cx, cy, self.inner_poly)

def point_in_polygon(x, y, poly):
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

class Car:
    def __init__(self, track):
        self.image_orig = car_img_orig
        self.x, self.y = track.start_pos
        self.angle = 0
        self.speed = 5
        self.laps = 0
        self.last_cross = False
        self.track = track
        self.start_time = time.time()

    def move(self, keys):
        if keys[pygame.K_w]:
            self.y -= self.speed
            self.angle = 0
        if keys[pygame.K_s]:
            self.y += self.speed
            self.angle = 180
        if keys[pygame.K_a]:
            self.x -= self.speed
            self.angle = 90
        if keys[pygame.K_d]:
            self.x += self.speed
            self.angle = -90

    def draw(self, surface):
        rotated = pygame.transform.rotate(self.image_orig, self.angle)
        rect = rotated.get_rect(center=(self.x, self.y))
        surface.blit(rotated, rect)

    def get_rect(self):
        rotated = pygame.transform.rotate(self.image_orig, self.angle)
        return rotated.get_rect(center=(self.x, self.y))

    def check_lap(self):
        rect = self.get_rect()
        if self.track.finish_line.colliderect(rect):
            if not self.last_cross:
                self.laps += 1
                self.last_cross = True
        else:
            self.last_cross = False

MENU = 'menu'
SELECT_TRACK = 'select_track'
PLAY = 'play'
GAME_OVER = 'game_over'

state = MENU

tracks = [Track(1), Track(2), Track(3)]
current_track_index = 0
track = tracks[current_track_index]
car = Car(track)

def draw_button(surface, rect, text, font, base_color, border_color):
    pygame.draw.rect(surface, base_color, rect)
    pygame.draw.rect(surface, border_color, rect, 3)
    text_surf = font.render(text, True, WHITE)
    text_rect = text_surf.get_rect(center=rect.center)
    surface.blit(text_surf, text_rect)

def draw_menu():
    screen.blit(menu_bg, (0, 0))
    start_button_rect = pygame.Rect(WIDTH//2 - 150, HEIGHT//2 - 50, 300, 80)
    draw_button(screen, start_button_rect, "НАЧАТЬ", font_medium, GRAY, WHITE)
    return start_button_rect

def draw_select_track():
    screen.blit(menu_bg, (0, 0))
    btn_w, btn_h = 300, 70
    spacing = 20
    buttons = []
    for i in range(len(tracks)):
        rect = pygame.Rect(WIDTH//2 - btn_w//2, 200 + i * (btn_h + spacing), btn_w, btn_h)
        draw_button(screen, rect, f"Трасса {i+1}", font_medium, GRAY, WHITE)
        buttons.append(rect)
    return buttons

def draw_game_over(stars, total_time):
    screen.fill(BLACK)
    finished_txt = font_big.render("Game Over!", True, WHITE)
    stars_txt = font_medium.render(f"Звезды: {stars}", True, YELLOW)
    time_txt = font_medium.render(f"Время: {total_time} сек", True, WHITE)
    retry_button = pygame.Rect(WIDTH//2 - 150, 400, 300, 70)
    menu_button = pygame.Rect(WIDTH//2 - 150, 500, 300, 70)

    screen.blit(finished_txt, finished_txt.get_rect(center=(WIDTH//2, 200)))
    screen.blit(stars_txt, stars_txt.get_rect(center=(WIDTH//2, 300)))
    screen.blit(time_txt, time_txt.get_rect(center=(WIDTH//2, 350)))
    draw_button(screen, retry_button, "Играть снова", font_medium, GRAY, WHITE)
    draw_button(screen, menu_button, "Меню", font_medium, GRAY, WHITE)
    return retry_button, menu_button

def calculate_stars(track_type, total_time):
    if track_type == 1 or track_type == 2:
        if total_time <= 12:
            return 3
        elif total_time <= 14:
            return 2
        else:
            return 1
    elif track_type == 3:
        if total_time <= 25:
            return 3
        elif total_time <= 30:
            return 2
        else:
            return 1

while True:
    keys = pygame.key.get_pressed()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if state == MENU:
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                start_btn = draw_menu()
                if start_btn.collidepoint(mx, my):
                    state = SELECT_TRACK

        elif state == SELECT_TRACK:
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                buttons = draw_select_track()
                for i, btn in enumerate(buttons):
                    if btn.collidepoint(mx, my):
                        current_track_index = i
                        track = tracks[current_track_index]
                        car = Car(track)
                        state = PLAY

        elif state == GAME_OVER:
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                retry_btn, menu_btn = draw_game_over(stars, total_time)
                if retry_btn.collidepoint(mx, my):
                    car = Car(track)
                    state = PLAY
                elif menu_btn.collidepoint(mx, my):
                    state = MENU

    if state == MENU:
        screen.fill(BLACK)
        draw_menu()

    elif state == SELECT_TRACK:
        screen.fill(BLACK)
        draw_select_track()

    elif state == PLAY:
        car.move(keys)
        if not track.is_on_road(car.get_rect()):
            state = GAME_OVER
            total_time = int(time.time() - car.start_time)
            stars = 1
        else:
            track.draw(screen)
            car.draw(screen)
            car.check_lap()

            laps_text = font_medium.render(f"Круги: {car.laps}/{track.laps_required}", True, WHITE)
            time_text = font_medium.render(f"Время: {int(time.time() - car.start_time)} сек", True, WHITE)
            screen.blit(laps_text, (10, 10))
            screen.blit(time_text, (10, 50))

            if car.laps >= track.laps_required:
                total_time = int(time.time() - car.start_time)
                stars = calculate_stars(track.type_id, total_time)
                state = GAME_OVER

    elif state == GAME_OVER:
        draw_game_over(stars, total_time)

    pygame.display.flip()
    clock.tick(FPS)
