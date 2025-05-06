from settings import *

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups, collision_sprites):
        super().__init__(groups)
        self.load_images()
        self.state, self.frame_index = 'right', 0
        self.image = pygame.image.load(join(  'images', 'player', 'down', '0.png')).convert_alpha()
        self.rect = self.image.get_rect(center=pos)
        self.hitbox_rect = self.rect.inflate(-60, -90)
        self.cheat_mode = False  # Không cheat

        # Movement
        self.direction = pygame.Vector2()
        self.speed = 500
        self.base_speed = 500  # Lưu tốc độ gốc
        self.collision_sprites = collision_sprites

        # Item effects
        self.pass_through = False  # Trạng thái đi xuyên vật thể từ vật phẩm
        self.effect_timers = {
            'move_speed': {'active': False, 'start_time': 0, 'duration': 10000},  # 10 giây
            'pass_through': {'active': False, 'start_time': 0, 'duration': 10000}
        }

    def load_images(self):
        self.frames = {'left': [], 'right': [], 'up': [], 'down': []}
        for state in self.frames.keys():
            for folder_path, sub_folders, file_names in walk(join(  'images', 'player', state)):
                if file_names:
                    for file_name in sorted(file_names, key=lambda name: int(name.split('.')[0])):
                        full_path = join(folder_path, file_name)
                        surf = pygame.image.load(full_path).convert_alpha()
                        self.frames[state].append(surf)

    def input(self):
        keys = pygame.key.get_pressed()
        self.direction.x = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a])
        self.direction.y = int(keys[pygame.K_DOWN] or keys[pygame.K_s]) - int(keys[pygame.K_UP] or keys[pygame.K_w])
        self.direction = self.direction.normalize() if self.direction else self.direction

        # Bật/tắt cheat phím c
        if keys[pygame.K_c]:
            self.cheat_mode = not self.cheat_mode
            pygame.time.delay(150)  # Tránh toggle liên tục

    def move(self, dt):
        self.hitbox_rect.x += self.direction.x * self.speed * dt
        if not (self.cheat_mode or self.pass_through):  # Bỏ qua va chạm nếu cheat hoặc pass_through
            self.collision('horizontal')

        self.hitbox_rect.y += self.direction.y * self.speed * dt
        if not (self.cheat_mode or self.pass_through):
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

    def animate(self, dt):
        # Get state
        if self.direction.x != 0:
            self.state = 'right' if self.direction.x > 0 else 'left'
        if self.direction.y != 0:
            self.state = 'down' if self.direction.y > 0 else 'up'

        # Animate
        self.frame_index = self.frame_index + 5 * dt if self.direction else 0
        self.image = self.frames[self.state][int(self.frame_index) % len(self.frames[self.state])]

    def activate_effect(self, effect_type):
        current_time = pygame.time.get_ticks()
        if effect_type == 'move_speed' and not self.effect_timers['move_speed']['active']:
            self.speed = min(self.speed + 50, 600)  # Tăng tốc, tối đa 600
            self.effect_timers['move_speed'] = {'active': True, 'start_time': current_time, 'duration': 10000}
            print(f"Move speed boosted! Speed: {self.speed} for 10s")
        elif effect_type == 'pass_through' and not self.effect_timers['pass_through']['active']:
            self.pass_through = True
            self.effect_timers['pass_through'] = {'active': True, 'start_time': current_time, 'duration': 10000}
            print("Pass-through activated for 10s!")

    def update_effect_timers(self):
        current_time = pygame.time.get_ticks()
        if self.effect_timers['move_speed']['active']:
            if current_time - self.effect_timers['move_speed']['start_time'] >= self.effect_timers['move_speed']['duration']:
                self.speed = self.base_speed
                self.effect_timers['move_speed']['active'] = False
                print(f"Move speed boost ended. Speed: {self.speed}")
        if self.effect_timers['pass_through']['active']:
            if current_time - self.effect_timers['pass_through']['start_time'] >= self.effect_timers['pass_through']['duration']:
                self.pass_through = False
                self.effect_timers['pass_through']['active'] = False
                print("Pass-through deactivated")

    def update(self, dt):
        self.input()
        self.move(dt)
        self.animate(dt)
        self.update_effect_timers()  # Kiểm tra hiệu ứng