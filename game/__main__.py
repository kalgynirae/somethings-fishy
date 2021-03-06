#!/usr/bin/env python3
from collections import defaultdict
import enum
from functools import partial
import itertools

import pyglet
from pyglet.sprite import Sprite
from pyglet.window import key

from . import maps

fps = 30

class Dir:
    sw, w, nw, s, none, n, se, e, ne = itertools.product(range(-1, 2), repeat=2)

class Color:
    black = (0, 0, 0, 255)
    white = (255, 255, 255, 255)

movement = {
    'h': Dir.w,
    'j': Dir.s,
    'k': Dir.n,
    'l': Dir.e,
    'a': Dir.w,
    's': Dir.s,
    'w': Dir.n,
    'd': Dir.e,
    key.MOTION_LEFT: Dir.w,
    key.MOTION_DOWN: Dir.s,
    key.MOTION_UP: Dir.n,
    key.MOTION_RIGHT: Dir.e,
}
_push = [5, 5, 5, 5, 5, 4, 4, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1]
#_push = [5, 5, 5, 4, 4, 4, 3, 3, 3, 2, 2, 2, 1, 1, 1]
_bounce = [4, -2, -1, -1]
gridsize = sum(_push)
width, height = 1280, 720
center = {'x': width // 2, 'y': height // 2}
instructioncenter = {'x': width // 2, 'y': 40}
gridwidth = width // gridsize
gridheight = height // gridsize
gridxoffset = (width - gridwidth * gridsize) // 2 + gridsize // 2
gridyoffset = (height - gridheight * gridsize) // 2 + gridsize // 2
images = {}
images['bg'] = pyglet.image.load('art/bg.png').get_texture()
images['fish-left'] = pyglet.image.load('art/fish-left.png').get_texture()
images['fish-right'] = images['fish-left'].get_transform(flip_x=True)
images['fish-front'] = pyglet.image.load('art/fish-front.png').get_texture()
images['field-yellow'] = pyglet.image.load('art/field-yellow.png').get_texture()
images['field-red'] = pyglet.image.load('art/field-red.png').get_texture()
images['field-purple'] = pyglet.image.load('art/field-purple.png').get_texture()
images['bubble1'] = pyglet.image.load('art/bubble1.png').get_texture()
images['bubble2'] = pyglet.image.load('art/bubble2.png').get_texture()
images['bubble3'] = pyglet.image.load('art/bubble3.png').get_texture()
images['bubble4'] = pyglet.image.load('art/bubble4.png').get_texture()
images['bubble5'] = pyglet.image.load('art/bubble3.png').get_texture()
images['bubble6'] = pyglet.image.load('art/bubble2.png').get_texture()
images['wall'] = pyglet.image.load('art/wall.png').get_texture()
images['bwall'] = pyglet.image.load('art/bubblewall.png').get_texture()
images['star1'] = pyglet.image.load('art/star1.png').get_texture()
images['star2'] = pyglet.image.load('art/star2.png').get_texture()
images['complete'] = pyglet.image.load('art/complete.png').get_texture()
images['title'] = pyglet.image.load('art/title.png').get_texture()
for image in images.values():
    image.anchor_x = image.width // 2
    image.anchor_y = image.height // 2
sounds = {}
sounds['music-intro'] = pyglet.media.load('sound/music-intro.wav')
sounds['music-loop'] = pyglet.media.load('sound/music-loop.wav')
for name in 'blip shortblip bubble star reset pop complete'.split():
    sound = pyglet.media.StaticSource(pyglet.media.load('sound/%s.wav' % name))
    sounds[name] = sound

_players = []
def playsounds(*names):
    player = pyglet.media.Player()
    _players.append(player)
    for name in names:
        player.queue(sounds[name])
    player.play()

_batches = defaultdict(pyglet.graphics.Batch)

label = partial(
    pyglet.text.Label,
    anchor_x='center',
    anchor_y='baseline',
    bold=True,
    font_size=8,
)
biglabel = partial(
    pyglet.text.Label,
    anchor_x='center',
    anchor_y='baseline',
    bold=True,
    font_size=18,
)


class CollisionRect:
    def __init__(self, obj):
        self.x = obj.x - obj.width // 2
        self.y = obj.y - obj.height // 2
        self.width = obj.width - 24
        self.height = obj.height - 24


_collisions = set()
def collides(a, b):
    arect = CollisionRect(a)
    brect = CollisionRect(b)
    does_collide = all([
        arect.x < brect.width + brect.x,
        arect.x + arect.width > brect.x,
        arect.y < brect.height + brect.y,
        arect.y + arect.height > brect.y,
    ])
    if does_collide:
        if (a, b) in _collisions:
            return False
        else:
            _collisions.add((a, b))
            return True
    else:
        if (a, b) in _collisions:
            _collisions.remove((a, b))
        return False


class Label:
    def __init__(self, *, text, offset=Dir.none, type=label):
        super().__init__()
        self.labels = [
            type(text, batch=_batches['label'], color=Color.black),
            type(text, batch=_batches['label'], color=Color.black),
            type(text, batch=_batches['label'], color=Color.black),
            type(text, batch=_batches['label'], color=Color.black),
            type(text, batch=_batches['label'], color=Color.black),
            type(text, batch=_batches['label'], color=Color.black),
            type(text, batch=_batches['label'], color=Color.black),
            type(text, batch=_batches['label'], color=Color.black),
            type(text, batch=_batches['label'], color=Color.white),
        ]
        self.shadowdirs = [
            Dir.w,
            Dir.s,
            Dir.n,
            Dir.e,
            Dir.nw,
            Dir.ne,
            Dir.se,
            Dir.sw,
            Dir.none,
        ]
        self.offset = offset

    def delete(self):
        for label in self.labels:
            label.delete()

    def place(self, x, y):
        ox, oy = self.offset
        for label, (dx, dy) in zip(self.labels, self.shadowdirs):
            label.x = x + dx + ox
            label.y = y + dy + oy

    def update(self, dt):
        pass


class Animated:
    def __init__(self, *, imageprefix, delay, **kwargs):
        batch = _batches[type(self).__name__.lower()]
        self.frames = [
            Sprite(image, batch=batch)
            for name, image in sorted(images.items())
            if name.startswith(imageprefix)
        ]
        super().__init__(
            **kwargs,
            width=self.frames[0].width,
            height=self.frames[0].height,
        )
        self.parts.extend(self.frames)
        self.delay = delay
        self.frame = 0
        self.paused = False
        self.act(self.animate_iter(), id='animation')

    def animate_iter(self):
        while True:
            if not self.paused:
                self.frame = (self.frame + 1) % len(self.frames)
                for sprite in self.frames:
                    sprite.visible = False
                self.frames[self.frame].visible = True
            for _ in range(self.delay):
                yield

    def pause_animation(self):
        self.paused = True


class Collidable:
    def collide(self, other):
        raise NotImplementedError

    def delete(self):
        self.world.collidables.remove(self)
        super().delete()

    def enter_world(self, world):
        super().enter_world(world)
        self.world.collidables.add(self)


class GridCollidable:
    def grid_collide(self, other):
        raise NotImplementedError


class Obj:
    def __init__(self, *, name=None, width, height):
        super().__init__()
        self._x, self._y = 0, 0
        self.width, self.height = width, height
        self.actions = {}
        self._ids = itertools.count()
        self.parts = []
        self.deleted = False
        self.disable_collision = False
        if name:
            self.label = Label(text=name, offset=(0, height // 2 + 4))
            self.parts.append(self.label)
        else:
            self.label = None

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    def act(self, iterator, *, id=None):
        if id is None:
            id = next(self._ids)
        self.actions[id] = iterator

    def check_collisions(self):
        if not self.disable_collision:
            for obj in self.world.collidables.copy():
                if obj == self:
                    continue
                if collides(self, obj):
                    obj.collide(self)
        for obj in self.world.neighbors(self):
            if isinstance(obj, GridCollidable):
                obj.grid_collide(self)

    def delete(self):
        if self.label is not None:
            self.label.delete()
        self.parts = [part for part in self.parts if not isinstance(part, Label)]
        self.act(self.delete_iter(), id='delete')

    def delete_iter(self):
        for _ in range(3):
            for part in self.parts:
                part.scale += 1
                part.opacity -= 64
            yield
        self.world.remove(self)
        for part in self.parts:
            part.delete()
        self.deleted = True

    def enter_world(self, world):
        self.world = world

    def is_done(self):
        return True

    def place(self, x, y):
        for part in self.parts:
            if isinstance(part, (Obj, Label)):
                part.place(x, y)
            else:
                part.x = x
                part.y = y
        self._x = x
        self._y = y

    def update(self, dt):
        for id, action in list(self.actions.items()):
            try:
                next(action)
            except StopIteration:
                del self.actions[id]
        if not self.deleted:
            self.check_collisions()


class Fish(Obj):
    def __init__(self, *, batch=None, **kwargs):
        batch = batch or _batches[type(self).__name__.lower()]
        self.sprites = {
            'left': Sprite(images['fish-left'], batch=batch),
            'front': Sprite(images['fish-front'], batch=batch),
            'right': Sprite(images['fish-right'], batch=batch),
        }
        super().__init__(**kwargs, height=images['fish-left'].height, width=images['fish-left'].width)
        for sprite in self.sprites.values():
            self.parts.append(sprite)
            sprite.anchor_x = sprite.width // 2
            sprite.anchor_y = sprite.height // 2
            sprite.visible = False
        self.sprites['left'].visible = True
        self.direction = 'left'
        self.disable_collision = False
        self.frozen = False

    def face(self, direction):
        dx, _ = direction
        if dx == 0:
            return
        elif dx < 0:
            newdir = 'left'
        elif dx > 0:
            newdir = 'right'
        if newdir != self.direction:
            self.act(self.face_iter(newdir), id='face')
            self.direction = newdir

    def face_iter(self, dir):
        self.sprites['left'].visible = False
        self.sprites['right'].visible = False
        self.sprites['front'].visible = True
        yield
        yield
        self.sprites['front'].visible = False
        self.sprites[dir].visible = True

    def move(self, dir):
        if self.world.try_move(self, dir):
            self.act(self.move_iter(dir, _push))
            return True
        else:
            self.act(self.move_iter(dir, _bounce))
            return False

    def move_iter(self, dir, amounts):
        for amount in amounts:
            dx, dy = dir
            new_x = self.x + dx*amount
            new_y = self.y + dy*amount
            self.place(new_x, new_y)
            yield


class Field(Collidable, Obj):
    def __init__(self, *, batch=None, state=0, **kwargs):
        super().__init__(**kwargs, height=images['field-red'].height, width=images['field-red'].width)
        batch = batch or _batches[type(self).__name__.lower()]
        self.sprites = [
            Sprite(images['field-yellow'], batch=batch),
            Sprite(images['field-red'], batch=batch),
            Sprite(images['field-purple'], batch=batch),
        ]
        self.parts.extend(self.sprites)
        self.advance(state)

    def advance(self, state=None):
        if state is None:
            state = (self.state + 1) % len(self.sprites)
            playsounds('blip')
        for sprite in self.sprites:
            sprite.visible = False
        self.sprites[state].visible = True
        self.state = state

    def collide(self, other):
        if isinstance(other, Fish):
            self.advance()

    def is_done(self):
        return self.state == 2


class Wall(Obj):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, width=images['wall'].width, height=images['wall'].height)
        self.sprite = Sprite(images['wall'], batch=_batches['wall'])
        self.parts.append(self.sprite)


class BubbleWall(Obj):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, width=images['bwall'].width, height=images['bwall'].height)
        self.sprite = Sprite(images['bwall'], batch=_batches['wall'])
        self.parts.append(self.sprite)


class Bubble(Animated, Collidable, GridCollidable, Obj):
    def __init__(self, **kwargs):
        super().__init__(
            **kwargs,
            imageprefix='bubble',
            delay=3,
        )
        self.captured = None

    def collide(self, other):
        if other == self.captured:
            other.disable_collision = True
            self.act(self.rise_iter(), id='rise')

    def grid_collide(self, other):
        if isinstance(other, Fish) and not other.frozen:
            other.frozen = True
            self.captured = other

    def rise_iter(self):
        while True:
            if self.world.try_move(self.captured, Dir.n):
                playsounds('bubble')
                yield from zip(
                    Fish.move_iter(self, Dir.n, _push),
                    self.captured.move_iter(Dir.n, _push),
                )
            else:
                break
        self.captured.frozen = False
        self.captured.disable_collision = False
        self.delete()
        playsounds('pop')


class Star(Animated, Collidable, Obj):
    def __init__(self, **kwargs):
        super().__init__(
            **kwargs,
            imageprefix='star',
            delay=10,
        )
        self.captured = None

    def collide(self, other):
        if isinstance(other, Fish) and not other.frozen:
            playsounds('star')
            self.delete()


class World:
    def __init__(self, *, maps):
        self.grid = defaultdict(set)
        self.width = gridwidth
        self.height = gridheight
        self.maps = maps
        self.mapindex = -1
        self.bg = Sprite(images['bg'], **center)
        self.title = Sprite(images['title'], **center)
        self.complete = Sprite(images['complete'], **center)
        self.complete.visible = False
        self.instruction = None
        self.window = pyglet.window.Window(width, height)

        self.set_instruction('Press <Space> or <Enter> to start')
        self.mode = 'stop'

        @self.window.event
        def on_draw():
            self.window.clear()
            self.bg.draw()
            _batches['field'].draw()
            _batches['wall'].draw()
            _batches['star'].draw()
            _batches['fish'].draw()
            _batches['bubble'].draw()
            _batches['label'].draw()
            self.complete.draw()
            self.title.draw()

        @self.window.event
        def on_key_press(symbol, modifiers):
            if symbol in [key.ESCAPE]:
                pyglet.clock.schedule(self.exit)

        @self.window.event
        def on_text(text):
            if text in ['q']:
                pyglet.clock.schedule(self.exit)
            elif (
                (self.mode == 'stop' and text in [' ', '\r']) or
                (self.mode == 'go' and text in ['[', ']'])
            ):
                if text == '[':
                    if self.mapindex > 0:
                        self.mapindex -= 1
                elif text == ']':
                    if self.mapindex < len(self.maps) - 1:
                        self.mapindex += 1
                else:
                    self.mapindex += 1
                if self.mapindex < len(self.maps):
                    self.reset()
                else:
                    self.mode = 'finished'
                    self.set_instruction('No further puzzles exist :(  Press Q to exit.')
            elif self.mode == 'go' and text in movement:
                if not self.player.frozen and not self.moved_this_update:
                    self.player.move(movement[text])
                    self.moved_this_update = True
                self.player.face(movement[text])
            elif self.mode == 'go' and text in ['r']:
                self.mode = 'reset'

        @self.window.event
        def on_text_motion(motion):
            on_text(motion)

        self.musicplayer = pyglet.media.Player()
        music = pyglet.media.SourceGroup(sounds['music-intro'].audio_format, None)
        music.queue(sounds['music-intro'])
        music.queue(sounds['music-loop'])
        self.musicplayer.queue(music)
        self.musicplayer.volume = 0.6
        self.musicplayer.play()

        @self.musicplayer.event
        def on_eos():
            music.loop = True

    def reset(self):
        for obj in self.objs():
            obj.delete()
        for player in _players:
            player.delete()
        _players.clear()
        _batches.clear()
        self.mode = 'go'
        self.set_instruction('Use ←↓↑→ or WASD to move. Press R to reset.')
        pyglet.clock.unschedule(self.update_all)
        pyglet.clock.schedule_interval(self.update_all, 1 / fps)
        self.complete.visible = False
        self.title.visible = False
        self.grid = defaultdict(set)
        self.collidables = set()
        self.moved_this_update = False
        self.player = Fish(name='T. Jefferson')
        for (gx, gy), char in maps.parse(self.maps[self.mapindex]):
            if char == 'y':
                self.spawn(Field, gx, gy, state=0)
            elif char == 'r':
                self.spawn(Field, gx, gy, state=1)
            elif char == 'p':
                self.spawn(Field, gx, gy, state=2)
            elif char == 's':
                self.put(self.player, gx, gy)
            elif char == 'o':
                self.spawn(Bubble, gx, gy)
            elif char == '#':
                self.spawn(Wall, gx, gy)
            elif char == '%':
                self.spawn(BubbleWall, gx, gy)
            elif char == '*':
                self.spawn(Star, gx, gy)
        playsounds('reset')

    def is_complete(self):
        return all(obj.is_done() for objs in self.grid.values() for obj in objs)

    def locate(self, obj):
        for loc, objs in self.grid.items():
            if obj in objs:
                return loc
        raise ValueError('{obj!r} is not in the grid')

    def neighbors(self, obj):
        return self.grid[self.locate(obj)] - {obj}

    def objs(self):
        return list(itertools.chain.from_iterable(map(list, self.grid.values())))

    def put(self, obj, gx, gy):
        self.grid[gx, gy].add(obj)
        obj.enter_world(self)
        x = gx * gridsize + gridxoffset
        y = gy * gridsize + gridyoffset
        obj.place(x, y)

    def remove(self, obj):
        gx, gy = self.locate(obj)
        self.grid[gx, gy].remove(obj)

    def set_instruction(self, text):
        if self.instruction is not None:
            self.instruction.delete()
        self.instruction = Label(text=text, type=biglabel)
        self.instruction.place(**instructioncenter)

    def spawn(self, type, gx, gy, **kwargs):
        self.put(type(**kwargs), gx, gy)

    def try_move(self, obj, dir):
        dx, dy = dir
        gx, gy = self.locate(obj)
        nx = gx + dx
        ny = gy + dy
        if 0 <= nx < self.width and 0 <= ny < self.height:
            if any(isinstance(o, (BubbleWall, Wall)) for o in self.grid[nx, ny]):
                if not (
                    any(isinstance(o, BubbleWall) for o in self.grid[nx, ny]) and
                    obj.frozen
                ):
                    return False
            self.grid[gx, gy].remove(obj)
            self.grid[nx, ny].add(obj)
            return True
        else:
            return False

    def update_all(self, dt):
        if self.mode == 'reset':
            self.reset()
        for obj in self.objs():
            obj.update(dt)
        if self.is_complete():
            self.mode = 'stop'
            pyglet.clock.unschedule(world.update_all)
            self.complete.visible = True
            self.set_instruction('Press <Space> or <Enter> to continue')
            playsounds('complete')
        self.moved_this_update = False

    def exit(self, dt):
        self.window.close()
        pyglet.app.exit()


world = World(maps=maps.maps)
pyglet.app.run()
