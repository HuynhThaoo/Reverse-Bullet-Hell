from settings import *
from player import Player
from menu import Menu
import os
import json
import pygame
from pygame import mixer
from sprites import *
from pytmx.util_pygame import load_pygame
from groups import AllSprites
from random import randint, choice

class Game:
    def __init__(self):
        pygame.init()
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Survivor')
        self.clock = pygame.time.Clock()
        self.running = True
        self.current_difficulty = 1
        self.menu = Menu(self)
        self.menu.run()
        self.paused = False
        self.invincible = False
        self.invincible_timer = 0

        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()
        self.item_sprites = pygame.sprite.Group()

        self.player_health = 3
        self.can_shoot = True
        self.shoot_time = 0
        self.auto_shoot_timer = 0
        self.auto_shoot_interval = 500
        self.base_shoot_interval = 500

        self.enemy_event = pygame.event.custom_type()
        self.enemy_spawn_rate = 1500
        self.max_enemies = 20

        pygame.time.set_timer(self.enemy_event, self.enemy_spawn_rate)
        self.spawn_positions = []
        self.previous_minutes = 0

        self.shoot_sound = pygame.mixer.Sound(join('..', 'audio', 'shoot.wav'))
        self.shoot_sound.set_volume(0.1)
        self.impact_sound = pygame.mixer.Sound(join('..', 'audio', 'impact.ogg'))
        self.music = pygame.mixer.Sound(join('..', 'audio', 'bs.mp3'))
        self.music.set_volume(0.2)
        self.music_playing = True

        self.effect_timers = {
            'shoot_speed': {'active': False, 'start_time': 0, 'duration': 10000}
        }

        self.load_images()
        self.setup()
        self.game_over = False
        self.start_time = pygame.time.get_ticks()
        self.elapsed_time = 0
        self.hit_count = 0

        self.item_message = None
        self.item_message_timer = 0
        self.item_message_duration = 2000

    def load_images(self):
        self.bullet_surf = pygame.image.load(join('..', 'images', 'gun', 'bullet.png')).convert_alpha()
        folders = next(walk(join('..', 'images', 'enemies')))[1]
        self.enemy_frames = {
            folder: [
                pygame.transform.scale(
                    pygame.image.load(join(folder_path, file_name)).convert_alpha(),
                    (132, 116)
                )
                for file_name in sorted(file_names, key=lambda name: int(name.split('.')[0]))
            ]
            for folder in folders
            for folder_path, _, file_names in walk(join('..', 'images', 'enemies', folder))
        }

    def setup(self):
        map = load_pygame(join('..', 'data', 'maps', 'world.tmx'))
        for sprite in self.enemy_sprites:
            sprite.health = 1
        for x, y, image in map.get_layer_by_name('Ground').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites)
        for obj in map.get_layer_by_name('Objects'):
            CollisionSprite((obj.x, obj.y), obj.image, (self.all_sprites, self.collision_sprites))
        for obj in map.get_layer_by_name('Collisions'):
            CollisionSprite((obj.x, obj.y), pygame.Surface((obj.width, obj.height)), self.collision_sprites)
        for obj in map.get_layer_by_name('Entities'):
            if obj.name == 'Player':
                self.player = Player((obj.x, obj.y), self.all_sprites, self.collision_sprites)
                self.gun = Gun(self.player, self.all_sprites)
            else:
                self.spawn_positions.append((obj.x, obj.y))
        if not self.music_playing:
            self.music.play(loops=-1)
            self.music_playing = True

    def increase_difficulty(self):
        enemy_health = min(7, self.hit_count // 15 + 1)
        self.current_difficulty = enemy_health
        for sprite in self.enemy_sprites:
            sprite.health = enemy_health
            # Tăng tốc độ quái
            if sprite.enemy_type == 'fast':
                sprite.speed = min(300, sprite.speed + 10)
            elif sprite.enemy_type == 'normal':
                sprite.speed = min(200, sprite.speed + 10)
            elif sprite.enemy_type == 'slow':
                sprite.speed = min(100, sprite.speed + 10)
        print(f"Difficulty increased! Enemies now require {enemy_health} hits, speed increased.")

    def auto_shoot(self):
        if self.game_over:
            return
        current_time = pygame.time.get_ticks()
        if current_time - self.auto_shoot_timer >= self.auto_shoot_interval and self.can_shoot:
            print(f"Current auto_shoot_interval: {self.auto_shoot_interval}")
            self.shoot_sound.play()
            pos = self.gun.rect.center + self.gun.player_direction * 50
            Bullet(self.bullet_surf, pos, self.gun.player_direction, (self.all_sprites, self.bullet_sprites))
            self.can_shoot = False
            self.shoot_time = pygame.time.get_ticks()
            self.auto_shoot_timer = current_time

    def display_item_effect(self, item_type):
        font = pygame.font.Font(None, 36)
        messages = {
            'health': 'Health +1!',
            'shoot_speed': 'Shoot Speed Up!',
            'move_speed': 'Move Speed Up!',
            'clear_enemies': 'Enemies Cleared!',
            'pass_through': 'Pass Through!'
        }
        self.item_message = font.render(messages[item_type], True, (255, 255, 255))
        self.item_message_timer = pygame.time.get_ticks()

    def gun_timer(self):
        if not self.can_shoot:
            current_time = pygame.time.get_ticks()
            if current_time - self.shoot_time >= self.auto_shoot_interval:
                self.can_shoot = True

    def bullet_collision(self):
        if self.bullet_sprites:
            for bullet in self.bullet_sprites:
                collision_sprites = pygame.sprite.spritecollide(bullet, self.enemy_sprites, False, pygame.sprite.collide_mask)
                if collision_sprites:
                    self.impact_sound.play()
                    bullet.kill()
                    for sprite in collision_sprites:
                        sprite.health -= 1
                        if sprite.health <= 0:
                            sprite.destroy()
                            Enemy.num_enemies_killed += 1
                            self.hit_count += 1
                            if random.random() < 0.20:
                                item_types = ['health', 'shoot_speed', 'move_speed', 'clear_enemies', 'pass_through']
                                weights = [0.30, 0.22, 0.28, 0.10, 0.10]
                                item_type = random.choices(item_types, weights=weights, k=1)[0]
                                Item(sprite.rect.center, (self.all_sprites, self.item_sprites), item_type)
                            if self.hit_count % 15 == 0 and self.hit_count <= 75:
                                current_interval = self.auto_shoot_interval
                                increase_percentage = 0.08
                                new_interval = max(250, current_interval * (1 - increase_percentage))
                                self.auto_shoot_interval = new_interval
                                self.base_shoot_interval = new_interval
                                print(f"Speed increased! New auto_shoot_interval: {new_interval:.1f}ms")
                            if self.hit_count % 10 == 0:
                                self.increase_difficulty()

    def item_collision(self):
        collided_items = pygame.sprite.spritecollide(self.player, self.item_sprites, True, pygame.sprite.collide_mask)
        current_time = pygame.time.get_ticks()
        for item in collided_items:
            if item.item_type == 'health':
                self.player_health = min(self.player_health + 1, 5)
                print(f"Health increased! Current health: {self.player_health}")
                self.display_item_effect(item.item_type)
            elif item.item_type == 'shoot_speed':
                if not self.effect_timers['shoot_speed']['active']:
                    self.auto_shoot_interval = max(250, self.auto_shoot_interval * 0.85)
                    self.effect_timers['shoot_speed'] = {'active': True, 'start_time': current_time, 'duration': 10000}
                    print(f"Shoot speed boosted! Interval: {self.auto_shoot_interval:.1f}ms for 10s")
                    self.display_item_effect(item.item_type)
            elif item.item_type == 'move_speed':
                self.player.activate_effect('move_speed')
                self.display_item_effect(item.item_type)
            elif item.item_type == 'clear_enemies':
                for enemy in self.enemy_sprites:
                    enemy.destroy()
                self.enemy_sprites.empty()
                self.enemy_spawn_rate = 1500
                pygame.time.set_timer(self.enemy_event, self.enemy_spawn_rate)
                print("All enemies cleared!")
                self.display_item_effect(item.item_type)
            elif item.item_type == 'pass_through':
                self.player.activate_effect('pass_through')
                self.display_item_effect(item.item_type)

    def update_effect_timers(self):
        current_time = pygame.time.get_ticks()
        if self.effect_timers['shoot_speed']['active']:
            if current_time - self.effect_timers['shoot_speed']['start_time'] >= self.effect_timers['shoot_speed']['duration']:
                self.auto_shoot_interval = self.base_shoot_interval
                self.effect_timers['shoot_speed']['active'] = False
                print(f"Shoot speed boost ended. Interval: {self.auto_shoot_interval:.1f}ms")

    def player_collision(self):
        if not self.invincible and pygame.sprite.spritecollide(self.player, self.enemy_sprites, False, pygame.sprite.collide_mask):
            self.player_health -= 1
            print(f"Player hit! Health: {self.player_health}")
            if self.player_health <= 0:
                self.game_over = True
            else:
                self.invincible = True
                self.invincible_timer = pygame.time.get_ticks()

    def update_invincibility(self):
        if self.invincible:
            current_time = pygame.time.get_ticks()
            if current_time - self.invincible_timer >= 1000:
                self.invincible = False

    def reset_game(self):
        self.music.stop()
        self.music_playing = False
        self.game_over = False
        self.enemy_spawn_rate = 1500
        self.previous_minutes = 0
        pygame.time.set_timer(self.enemy_event, self.enemy_spawn_rate)
        self.hit_count = 0
        self.current_difficulty = 1
        self.auto_shoot_interval = 500
        self.base_shoot_interval = 500
        self.player_health = 3
        self.invincible = False
        Enemy.num_enemies_killed = 0
        self.effect_timers = {
            'shoot_speed': {'active': False, 'start_time': 0, 'duration': 10000}
        }
        print("Game reset to default state")
        self.all_sprites.empty()
        self.collision_sprites.empty()
        self.bullet_sprites.empty()
        self.enemy_sprites.empty()
        self.item_sprites.empty()
        self.start_time = pygame.time.get_ticks()
        self.elapsed_time = 0
        self.item_message = None
        self.item_message_timer = 0
        self.setup()

    def run(self):
        self.music.play(loops=-1)
        while self.running:
            dt = self.clock.tick() / 1000
            if not self.game_over:
                self.elapsed_time = pygame.time.get_ticks() - self.start_time
            minutes = self.elapsed_time // 60000
            if minutes > self.previous_minutes:
                self.previous_minutes = minutes
                self.enemy_spawn_rate = max(300, self.enemy_spawn_rate - 50)
                pygame.time.set_timer(self.enemy_event, self.enemy_spawn_rate)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == self.enemy_event:
                    if len(self.enemy_sprites) < self.max_enemies:
                        camera_rect = pygame.Rect(
                            self.player.rect.centerx - WINDOW_WIDTH // 2,
                            self.player.rect.centery - WINDOW_HEIGHT // 2,
                            WINDOW_WIDTH,
                            WINDOW_HEIGHT
                        )
                        valid_spawn_positions = [pos for pos in self.spawn_positions if not camera_rect.collidepoint(pos)]
                        if valid_spawn_positions:
                            spawn_position = choice(valid_spawn_positions)
                            enemy_type = random.choices(
                                ["fast", "normal", "slow"],
                                weights=[0.3, 0.4, 0.3],
                                k=1
                            )[0]
                            enemy = Enemy(
                                spawn_position,
                                choice(list(self.enemy_frames.values())),
                                (self.all_sprites, self.enemy_sprites),
                                self.player,
                                self.collision_sprites,
                                enemy_type=enemy_type
                            )
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        self.paused = not self.paused
                        if self.paused and not self.music_playing:
                            self.music.stop()
                            self.music_playing = False
                        elif not self.paused and not self.music_playing:
                            self.music.play(loops=-1)
                            self.music_playing = True
                    elif event.key == pygame.K_SPACE:
                        self.music.stop()
                        self.music_playing = False
                    elif event.key == pygame.K_r:
                        self.reset_game()
                    elif event.key == pygame.K_m:
                        self.music.stop()
                        self.music_playing = True
                        self.menu.run()
                        self.music.play(loops=-1)
                    elif event.key == pygame.K_x:
                        self.running = False

            if not self.game_over and not self.paused:
                self.gun_timer()
                self.auto_shoot()
                self.all_sprites.update(dt)
                self.item_sprites.update(dt)
                self.update_invincibility()
                self.bullet_collision()
                self.player_collision()
                self.item_collision()
                self.update_effect_timers()
            else:
                if self.paused and self.music_playing:
                    self.music.stop()
                    self.music_playing = False

            self.display_surface.fill('black')
            self.all_sprites.draw(self.player.rect.center)
            self.display_time_and_hits()

            if self.item_message and pygame.time.get_ticks() - self.item_message_timer < self.item_message_duration:
                self.display_surface.blit(self.item_message, (WINDOW_WIDTH // 2 - 50, 50))
            else:
                self.item_message = None

            if self.paused:
                pause_font = pygame.font.Font(None, 60)
                pause_text = pause_font.render('Paused', True, (255, 255, 0))
                pause_rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
                self.display_surface.blit(pause_text, pause_rect)
            if self.game_over:
                self.display_game_over()

            pygame.display.update()

        pygame.quit()

    def display_game_over(self):
        self.music.stop()
        self.music_playing = False
        self.display_surface.fill((0, 0, 0))

        high_score = self.get_high_score()
        is_new_high_score = self.hit_count > high_score

        if is_new_high_score:
            self.save_high_score(self.hit_count)
            high_score = self.hit_count

        font = pygame.font.Font(None, 74)
        text = font.render('Game Over', True, (255, 0, 0))
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3))
        self.display_surface.blit(text, text_rect)

        score_font = pygame.font.Font(None, 48)
        score_text = score_font.render(f'Score: {self.hit_count}', True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3 + 60))
        self.display_surface.blit(score_text, score_rect)

        high_score_text = score_font.render(f'High Score: {high_score}', True, (255, 255, 0))
        high_score_rect = high_score_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3 + 110))
        self.display_surface.blit(high_score_text, high_score_rect)

        if is_new_high_score:
            new_high_score_text = score_font.render('New High Score!', True, (255, 215, 0))
            new_high_score_rect = new_high_score_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3 + 160))
            self.display_surface.blit(new_high_score_text, new_high_score_rect)

        restart_text = font.render('Press R to Restart', True, (255, 255, 255))
        restart_text_rect = restart_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3 + 230))
        self.display_surface.blit(restart_text, restart_text_rect)

        exit_text = font.render('Press X to Exit', True, (255, 255, 255))
        exit_text_rect = exit_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3 + 290))
        self.display_surface.blit(exit_text, exit_text_rect)

    def display_time_and_hits(self):
        font = pygame.font.Font(None, 36)
        time_text = font.render(f"Time: {self.elapsed_time // 1000}s", True, (255, 255, 255))
        self.display_surface.blit(time_text, (10, 10))
        hit_count_text = font.render(f"Eliminated: {self.hit_count} enemies", True, (255, 255, 255))
        self.display_surface.blit(hit_count_text, (10, 50))
        health_text = font.render(f"Health: {self.player_health}", True, (255, 255, 255))
        self.display_surface.blit(health_text, (10, 90))

    def save_high_score(self, score):
        high_scores = {}
        if os.path.exists('high_scores.json'):
            with open('high_scores.json', 'r') as file:
                high_scores = json.load(file)
        current_high_score = high_scores.get('high_score', 0)
        if score > current_high_score:
            high_scores['high_score'] = score
            with open('high_scores.json', 'w') as file:
                json.dump(high_scores, file)
            return True
        return False

    def get_high_score(self):
        if os.path.exists('high_scores.json'):
            with open('high_scores.json', 'r') as file:
                high_scores = json.load(file)
                return high_scores.get('high_score', 0)
        return 0

if __name__ == '__main__':
    game = Game()
    game.run()