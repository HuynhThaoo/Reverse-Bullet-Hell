from settings import *
from math import atan2, degrees
import random
import pygame

class Sprite(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft=pos)
        self.ground = True

class CollisionSprite(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft=pos)

class Gun(pygame.sprite.Sprite):
    def __init__(self, player, groups):
        self.player = player 
        self.distance = 140
        self.player_direction = pygame.Vector2(0, 1)

        super().__init__(groups)
        self.gun_surf = pygame.image.load(join(  'images', 'gun', 'gun.png')).convert_alpha()
        new_width = self.gun_surf.get_width() // 2
        new_height = self.gun_surf.get_height() // 2
        self.gun_surf = pygame.transform.scale(self.gun_surf, (new_width, new_height))
        self.image = self.gun_surf
        self.rect = self.image.get_rect(center=(self.player.rect.center + self.player_direction * self.distance))
    
    def get_direction(self):
        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        player_pos = pygame.Vector2(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
        direction = mouse_pos - player_pos
        self.player_direction = direction.normalize() if direction.length() != 0 else pygame.Vector2(0, 1)

    def rotate_gun(self):
        angle = degrees(atan2(self.player_direction.x, self.player_direction.y)) - 90
        if self.player_direction.x > 0:
            self.image = pygame.transform.rotozoom(self.gun_surf, angle, 1)
        else:
            self.image = pygame.transform.rotozoom(self.gun_surf, abs(angle), 1)
            self.image = pygame.transform.flip(self.image, False, True)

    def update(self, dt):
        self.get_direction()
        self.rotate_gun()
        self.rect.center = self.player.rect.center + self.player_direction * self.distance

class Bullet(pygame.sprite.Sprite):
    def __init__(self, surf, pos, direction, groups):
        super().__init__(groups)
        self.image = surf 
        self.rect = self.image.get_rect(center=pos)
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = 1000
        self.direction = direction 
        self.speed = 1200 
    
    def update(self, dt):
        self.rect.center += self.direction * self.speed * dt
        if pygame.time.get_ticks() - self.spawn_time >= self.lifetime:
            self.kill()

class Enemy(pygame.sprite.Sprite):
    num_enemies_killed = 0

    def __init__(self, pos, frames, groups, player, collision_sprites, enemy_type="normal", health=1):
        super().__init__(groups)
        self.player = player
        self.enemy_type = enemy_type

        # image 
        self.frames, self.frame_index = frames, 0 
        self.image = self.frames[self.frame_index]
        self.animation_speed = 10
        self.original_image = self.image.copy()

        # Thiết lập máu
        if self.enemy_type == "fast":
            self.health = max(1, health - 1)  # Nhanh nhưng yếu hơn
            self.speed = 210
        elif self.enemy_type == "slow":
            self.health = health  # Đồng bộ với normal
            self.speed = 75
        else:  # normal
            self.health = health
            self.speed = 100

        self.rect = self.image.get_rect(center=pos)
        self.hitbox_rect = self.rect.inflate(-20, -40)
        self.collision_sprites = collision_sprites
        self.direction = pygame.Vector2()

        self.death_time = 0
        self.death_duration = 100

    def animate(self, dt):
        self.frame_index += self.animation_speed * dt
        current_frame = self.frames[int(self.frame_index) % len(self.frames)]
        self.original_image = current_frame.copy()
        self.image = self.original_image.copy()

    def move(self, dt):
        player_pos = pygame.Vector2(self.player.rect.center)
        enemy_pos = pygame.Vector2(self.rect.center)
        direction = player_pos - enemy_pos
        self.direction = direction.normalize() if direction.length() != 0 else pygame.Vector2(0, 1)

        self.hitbox_rect.x += self.direction.x * self.speed * dt
        self.collision('horizontal')
        self.hitbox_rect.y += self.direction.y * self.speed * dt
        self.collision('vertical')

        self.rect.center = self.hitbox_rect.center

    def collision(self, direction):
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.hitbox_rect):
                if direction == 'horizontal':
                    if self.direction.x > 0: self.hitbox_rect.right = sprite.rect.left
                    if self.direction.x < 0: self.hitbox_rect.left = sprite.rect.right
                else:
                    if self.direction.y < 0: self.hitbox_rect.top = sprite.rect.bottom
                    if self.direction.y > 0: self.hitbox_rect.bottom = sprite.rect.top

    def destroy(self):
        self.death_time = pygame.time.get_ticks()
        surf = pygame.mask.from_surface(self.frames[0]).to_surface()
        surf.set_colorkey('black')
        self.image = surf
        Enemy.num_enemies_killed += 1
        print(f"Destroyed {self.enemy_type} enemy with health: {self.health}")

    def death_timer(self):
        if pygame.time.get_ticks() - self.death_time >= self.death_duration:
            self.kill()

    def update(self, dt):
        self.image = self.original_image.copy()
        if self.death_time == 0:
            self.move(dt)
            self.animate(dt)
            if self.enemy_type == "fast":
                pygame.draw.rect(self.image, (255, 0, 0), self.image.get_rect(), 2)
            elif self.enemy_type == "slow":
                pygame.draw.rect(self.image, (0, 0, 255), self.image.get_rect(), 2)
        else:
            self.death_timer()

        font = pygame.font.Font(None, 40)
        health_text = font.render(str(self.health), True, (255, 0, 0))
        text_rect = health_text.get_rect(center=(self.image.get_width() // 2, 10))
        self.image.blit(health_text, text_rect)

class Item(pygame.sprite.Sprite):
    def __init__(self, pos, groups, item_type):
        super().__init__(groups)
        self.item_type = item_type
        try:
            self.image = pygame.image.load(join(  'images', 'item', 'hehe.png')).convert_alpha()
        except FileNotFoundError:
            self.image = pygame.Surface((32, 32))
            self.image.fill((255, 215, 0))  # Vàng cho hộp quà (tạm)
        
        self.image = pygame.transform.scale(self.image, (50, 50))
        self.rect = self.image.get_rect(center=pos)
        self.creation_time = pygame.time.get_ticks()
        self.lifetime = 5000  # Tồn tại 5 giây

    def update(self, dt):
        current_time = pygame.time.get_ticks()
        if current_time - self.creation_time >= self.lifetime:
            self.kill()