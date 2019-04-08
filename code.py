from math import floor
from random import randint
from tkinter import *
from PIL.Image import FLIP_LEFT_RIGHT
from tkinter.messagebox import askyesno
from _pickle import Pickler, Unpickler
from os.path import lexists

from PIL.ImageTk import *

MAX_LEVELS = 50
TICKTIME = 33
RIGHT_SIDE = 640
LEFT_SIDE = 0
IMG_LOCATION = r'pics\anim'

BIG_FONT = ('system', 24)
REG_FONT = ('system', 16)

SAVENAME = 'save'

window = Tk()
window.geometry('640x480')
canvas = Canvas(window)
canvas.pack(expand=True, fill=BOTH)

def isempty(lst):
	return not len(lst)

def remove(elem, lst):
	if elem in lst:
		lst.remove(elem)

def add(elem, lst):
	if elem not in lst:
		lst.append(elem)

def clear(lst):
	lst.clear()

#get frames from gif and put in dict. [state] = [frames]
def extractframes(gifs):
	frames = {'L': {}, 'R': {}}

	#extract frames from gifs.
	for state in gifs:
		image = Image.open(IMG_LOCATION + gifs[state])
		seq = {'L': [], 'R': []}
		try:
			while True:
				seq['L'].append(image.copy())
				seq['R'].append(image.transpose(FLIP_LEFT_RIGHT))
				image.seek(len(seq['L']))  # skip to next frame
		except EOFError:
			pass

		#extract for each sirection.
		for face in 'LR':
			frames[face][state] = [PhotoImage(seq[face][0])]
			temp = seq[face][0]
			for image in seq[face][1:]:
				temp.paste(image)
				frames[face][state].append(PhotoImage(temp))

	return frames

def draw(lanenum, pos, photo, anchor='s'):
	if lanenum is 1:
		y = 195
	elif lanenum is 2:
		y = 275
	else:
		y = 355

	#draw shadow.
	canvas.create_image((pos, y), image=shadowpic, anchor='s')

	#draw photo.
	canvas.create_image((pos, y), image=photo, anchor=anchor)


class Unit(object):
	def __init__(self, frames, hp, atk, range, aspd, mspd, lanenum, isplayer, missle=None):
		self.hp = hp
		self.atk = atk
		self.range = range
		self.lanenum = lanenum
		self.isplayer = isplayer
		self.pos = LEFT_SIDE if self.isplayer else RIGHT_SIDE
		self.missle = missle

		add(self, lanes[self.lanenum])

		self.state = ''
		self.frameidx = 0
		self.speeds = {'move': mspd, 'attack' : aspd, 'pick': 10, 'hurt': 10, 'die': 10}
		self.meters = {'move': 0, 'attack' : 0, 'pick': 0, 'hurt': 0, 'die': 0}

		self.frames = frames['R' if self.isplayer else 'L']

	def shoot(self):
		if self.animate('attack') == 1:
			self.missle(lanenum=self.lanenum, pos=self.pos, isplayer=self.isplayer, targetpos=self.pos + self.range if self.isplayer else self.pos - self.range, atk=self.atk)

	def animate(self, state, loop=True):
		checkpoint = None
		if self.state == state:
			next = self.meters[state] + self.speeds[state]
			if next >= 100:
				checkpoint = 1
			elif self.meters[state] < 66 and next >= 66:
				checkpoint = 2 / 3
			elif self.meters[state] < 50 and next >= 50:
				checkpoint = 1 / 2
			elif self.meters[state] < 33 and next >= 33:
				checkpoint = 1 / 3
			self.meters[state] = next
			self.meters[state] %= 100
			self.frameidx = floor(self.meters[state] * len(self.frames[self.state]) / 100)
		else:
			self.meters[state] = 0
			self.frameidx = 0
			self.state = state

		if loop or checkpoint != 1:
			draw(self.lanenum, self.pos, self.frames[self.state][self.frameidx], anchor=None if self.state == 'die' else 's')
		else:
			draw(self.lanenum, self.pos, self.frames[self.state][len(self.frames[self.state]) - 1], anchor=None if self.state == 'die' else 's')

		return checkpoint

	def move(self):
		self.animate('move')
		if self.isplayer:
			self.pos += self.speeds['move']
		else:
			self.pos -= self.speeds['move']

	def attack(self, target):
		if self.animate('attack') == 1 / 2:
			target.hp -= self.atk
			if target.state != 'attack':
				target.state = 'hurt'

	def die(self):
		if self.animate('die', loop=False) == 1:
			remove(self, lanes[self.lanenum])
			self.pos = None

			#reward player money if self is enemy.
			if not self.isplayer and self.hp <= 0:
				global money
				money += self.__class__.cost

	def reachedotherside(self):
		if self.isplayer:
			enemyteam.life -= self.__class__.cost
		else:
			playerteam.life -= self.__class__.cost
		self.pos = None
		remove(self, lanes[self.lanenum])

	def gettargets(self):
		if self.isplayer:
			lst = [obj for obj in lanes[self.lanenum] if isinstance(obj, Unit) and obj.hp > 0 and not obj.isplayer and self.pos < obj.pos and self.pos + self.range >= obj.pos]
		else:
			lst = [obj for obj in lanes[self.lanenum] if isinstance(obj, Unit) and obj.hp > 0 and obj.isplayer and self.pos > obj.pos and self.pos - self.range <= obj.pos]
		return sorted(lst, key=lambda unit: abs(unit.pos - self.pos)) #order by closest

	def run(self):
		#die if dead.
		if self.hp <= 0:
			self.die()

		#reached other side.
		elif self.pos >= RIGHT_SIDE if self.isplayer else self.pos <= LEFT_SIDE:
			self.reachedotherside()

		#not reached end.
		else:
			enemiesinrange = self.gettargets()

			#hurt case.
			if self.state == 'hurt':
				if self.animate('hurt', loop=False) == 1:
					self.state = 'move'

			#attack case.
			elif not isempty(enemiesinrange):
				self.attack(enemiesinrange[0]) if self.missle is None else self.shoot()

			#finish attacking case.
			elif self.state == 'attack' and self.missle is None:
				if self.animate('attack') == 1:
					self.state = 'move'

			#move case.
			else:
				self.move()


class Swordsman(Unit):
	frames = extractframes({'move': r'\chars\swordsman_move.gif', 'attack': r'\chars\swordsman_attack.gif', 'hurt': r'\chars\swordsman_hurt.gif', 'die': r'\chars\swordsman_die.gif'})
	cost = 5
	hp = 10
	atk = 4
	range = 60
	mspd = 2.5
	aspd = 4
	level = 1
	desc = 'Basic unit.'
	portrait = PhotoImage(Image.open(r'pics\swordsmanhead.png'))
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Swordsman.frames, hp=Swordsman.hp, atk=Swordsman.atk, range=Swordsman.range, aspd=Swordsman.aspd, mspd=Swordsman.mspd, isplayer=isplayer, lanenum=lanenum)

class Archer(Unit):
	frames = extractframes({'move': r'\chars\archer_move.gif', 'attack': r'\chars\archer_attack.gif', 'hurt': r'\chars\archer_hurt.gif', 'die': r'\chars\archer_die.gif'})
	cost = 10
	hp = 10
	atk = 8
	range = 200
	mspd = 2.5
	aspd = 4
	level = 1
	desc = 'Ranged attacker.'
	portrait = PhotoImage(Image.open(r'pics\archerhead.png'))
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Archer.frames, hp=Archer.hp, atk=Archer.atk, range=Archer.range, aspd=Archer.aspd, mspd=Archer.mspd, isplayer=isplayer, lanenum=lanenum, missle=Arrow)

class Prophet(Unit):
	frames = extractframes({'move': r'\chars\mage_move.gif', 'attack': r'\chars\mage_attack.gif', 'hurt': r'\chars\mage_hurt.gif', 'die': r'\chars\mage_die.gif'})
	cost = 20
	hp = 15
	atk = 20
	range = 300
	mspd = 3
	aspd = 2
	level = 1
	desc = 'Hurls area of effect fireballs.'
	portrait = PhotoImage(Image.open(r'pics\magehead.png'))
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Prophet.frames, hp=Prophet.hp, atk=Prophet.atk, range=Prophet.range, aspd=Prophet.aspd, mspd=Prophet.mspd, isplayer=isplayer, lanenum=lanenum, missle=Fireball)


class Assassin(Unit):
	frames = extractframes({'move': r'\chars\assassin_move.gif', 'attack': r'\chars\assassin_attack.gif', 'hurt': r'\chars\assassin_hurt.gif', 'die': r'\chars\assassin_die.gif'})
	cost = 15
	hp = 20
	atk = 12
	range = 50
	mspd = 3.5
	aspd = 6.6
	level = 1
	desc = 'Fast attacker.'
	portrait = PhotoImage(Image.open(r'pics\assassinhead.png'))
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Assassin.frames, hp=Assassin.hp, atk=Assassin.atk, range=Assassin.range, aspd=Assassin.aspd, mspd=Assassin.mspd, isplayer=isplayer, lanenum=lanenum)

	def attack(self, target):
		result = self.animate('attack')

		if result == 1 / 3:
			target.hp -= self.atk / 2
			if target.state != 'attack':
				target.state = 'hurt'

		if result == 2 / 3:
			target.hp -= self.atk / 2
			if target.state != 'attack':
				target.state = 'hurt'

class Knight(Unit):
	frames = extractframes({'move': r'\chars\knight_peco_move.gif', 'attack': r'\chars\knight_peco_attack.gif', 'hurt': r'\chars\knight_peco_hurt.gif', 'die': r'\chars\knight_peco_die.gif'})
	cost = 15
	hp = 30
	atk = 7
	range = 110
	mspd = 5.5
	aspd = 4.5
	level = 1
	desc = 'Unit that charges to the finish.'
	portrait = PhotoImage(Image.open(r'pics\knighthead.png'))
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Knight.frames, hp=Knight.hp, atk=Knight.atk, range=Knight.range, aspd=Knight.aspd, mspd=Knight.mspd, isplayer=isplayer, lanenum=lanenum)

class Crusader(Unit):
	frames = extractframes({'move': r'\chars\crusader_move.gif', 'attack': r'\chars\crusader_attack.gif', 'hurt': r'\chars\crusader_hurt.gif', 'die': r'\chars\crusader_die.gif'})
	cost = 15
	hp = 40
	atk = 8
	range = 60
	mspd = 2
	aspd = 4
	level = 1
	desc = 'Meaty unit.'
	portrait = PhotoImage(Image.open(r'pics\crusaderhead.png'))
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Crusader.frames, hp=Crusader.hp, atk=Crusader.atk, range=Crusader.range, aspd=Crusader.aspd, mspd=Crusader.mspd, isplayer=isplayer, lanenum=lanenum)

class Barbarian(Unit):
	frames = extractframes({'move': r'\chars\barbarian_move.gif', 'attack': r'\chars\barbarian_attack.gif', 'hurt': r'\chars\barbarian_hurt.gif', 'die': r'\chars\barbarian_die.gif'})
	cost = 25
	hp = 30
	atk = 25
	range = 60
	mspd = 3
	aspd = 5
	level = 1
	desc = 'High attack unit.'
	portrait = PhotoImage(Image.open(r'pics\barbarianhead.png'))

	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Barbarian.frames, hp=Barbarian.hp, atk=Barbarian.atk, range=Barbarian.range, aspd=Barbarian.aspd, mspd=Barbarian.mspd, isplayer=isplayer, lanenum=lanenum)

	def attack(self, target):
		if self.animate('attack') == 1 / 3:
			target.hp -= self.atk
			if target.state != 'attack':
				target.state = 'hurt'

class Champion(Unit):
	frames = extractframes({'move': r'\chars\champion_move.gif', 'attack': r'\chars\champion_attack.gif', 'hurt': r'\chars\champion_hurt.gif', 'die': r'\chars\champion_die.gif'})
	cost = 25
	hp = 50
	atk = 200
	range = 50
	mspd = 3
	aspd = 1
	level = 1
	desc = 'Very slow attack but strong. Good against bosses.'
	portrait = PhotoImage(Image.open(r'pics\championhead.png'))

	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Champion.frames, hp=Champion.hp, atk=Champion.atk, range=Champion.range, aspd=Champion.aspd, mspd=Champion.mspd, isplayer=isplayer, lanenum=lanenum)

	def attack(self, target):
		if self.animate('attack') == 2 / 3:
			target.hp -= self.atk
			target.state = 'hurt'
			self.pos = self.pos + 100 if self.isplayer else self.pos - 100

class Taekwon(Unit):
	frames = extractframes({'move': r'\chars\taekwon_move.gif', 'attack': r'\chars\taekwon_attack.gif', 'hurt': r'\chars\taekwon_hurt.gif', 'die': r'\chars\taekwon_die.gif'})
	cost = 10
	hp = 20
	atk = 5
	range = 60
	mspd = 3
	aspd = 4
	level = 1
	desc = 'Adds pushback effect to every attack.'
	portrait = PhotoImage(Image.open(r'pics\taekwonhead.png'))

	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Taekwon.frames, hp=Taekwon.hp, atk=Taekwon.atk, range=Taekwon.range, aspd=Taekwon.aspd, mspd=Taekwon.mspd, isplayer=isplayer, lanenum=lanenum)

	def attack(self, target):
		if self.animate('attack') == 1 / 2:
			target.hp -= self.atk
			target.state = 'hurt'
			target.pos = target.pos + 100 if self.isplayer else target.pos - 100

class Rifleman(Unit):
	frames = extractframes({'move': r'\chars\gunslinger_move.gif', 'attack': r'\chars\gunslinger_attack.gif', 'hurt': r'\chars\gunslinger_hurt.gif', 'die': r'\chars\gunslinger_die.gif'})
	cost = 20
	hp = 30
	atk = 20
	range = 250
	mspd = 3
	aspd = 2
	level = 1
	desc = 'Ranged unit.'
	portrait = PhotoImage(Image.open(r'pics\gunslingerhead.png'))

	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Rifleman.frames, hp=Rifleman.hp, atk=Rifleman.atk, range=Rifleman.range, aspd=Rifleman.aspd, mspd=Rifleman.mspd, isplayer=isplayer, lanenum=lanenum)

class Priest(Unit):
	frames = extractframes({'move': r'\chars\priest_move.gif', 'attack': r'\chars\priest_attack.gif', 'hurt': r'\chars\priest_hurt.gif', 'die': r'\chars\priest_die.gif'})
	cost = 10
	hp = 15
	atk = 10
	range = 200
	mspd = 2
	aspd = 5
	level = 1
	desc = 'Heals closest following friendly unit.'
	portrait = PhotoImage(Image.open(r'pics\priesthead.png'))

	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Priest.frames, hp=Priest.hp, atk=Priest.atk, range=Priest.range, aspd=Priest.aspd, mspd=Priest.mspd, isplayer=isplayer, lanenum=lanenum)
		self.speeds['hurt'] = 5

	def attack(self, target):
		if self.animate('attack') == 1 / 2:
			if target.hp < target.__class__.hp:
				target.hp += self.atk

	def gettargets(self):
		if self.isplayer:
			lst = [obj for obj in lanes[self.lanenum] if isinstance(obj, Unit) and obj.isplayer and obj.hp > 0 and self.pos < obj.pos and self.pos + self.range >= obj.pos]
		else:
			lst = [obj for obj in lanes[self.lanenum] if isinstance(obj, Unit) and not obj.isplayer and obj.hp > 0 and self.pos > obj.pos and self.pos - self.range <= obj.pos]
		return sorted(lst, key=lambda unit: abs(unit.pos - self.pos)) #order by closest

class Minstrel(Unit):
	frames = extractframes({'move': r'\chars\minstrel_attack.gif', 'attack': r'\chars\minstrel_attack.gif', 'hurt': r'\chars\minstrel_hurt.gif', 'die': r'\chars\minstrel_die.gif'})
	cost = 20
	hp = 30
	atk = 0
	range = 1000
	mspd = 1
	aspd = 5
	level = 1
	desc = 'Increases attack speed of all friendly units in same lane.'
	portrait = PhotoImage(Image.open(r'pics\minstrelhead.png'))

	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Minstrel.frames, hp=Minstrel.hp, atk=Minstrel.atk, range=Minstrel.range, aspd=Minstrel.aspd, mspd=Minstrel.mspd, isplayer=isplayer, lanenum=lanenum)
		self.units = []
		self.speeds['hurt'] = 5

	def move(self):
		self.animate('move')
		for obj in lanes[self.lanenum]:
			if isinstance(obj, Unit):
				if (self.isplayer and obj.isplayer) or (not self.isplayer and not obj.isplayer):
					if obj not in self.units:
						add(obj, self.units)
						obj.speeds['attack'] += 1
		if self.isplayer:
			self.pos += self.speeds['move']
		else:
			self.pos -= self.speeds['move']

	def gettargets(self):
		return []

	def die(self):
		super().die()
		for unit in self.units:
			unit.speeds['attack'] -= 1
		clear(self.units)

	def reachedotherside(self):
		super().reachedotherside()
		for unit in self.units:
			unit.speeds['attack'] -= 1
		clear(self.units)



class Missle:
	#states: 'move', 'explode'
	def __init__(self, mspd, aspd, frames, atk, aoe, lanenum, pos, isplayer, targetpos):
		self.mspd = mspd
		self.aspd = aspd
		self.atk = atk
		self.aoe = aoe
		self.lanenum = lanenum
		self.pos = pos
		self.targetpos = targetpos

		self.meters = {'move': 0, 'explode': 0}
		self.speeds = {'move': mspd, 'explode': aspd}

		self.state = 'move'

		self.isplayer = isplayer
		self.frames = frames['R' if self.isplayer else 'L']

		add(self, lanes[lanenum])

	def animate(self, state, loop=True):
		checkpoint = None
		if self.state == state:
			next = self.meters[state] + self.speeds[state]
			if next >= 100:
				checkpoint = 1
			elif self.meters[state] < 66 and next >= 66:
				checkpoint = 2 / 3
			elif self.meters[state] < 50 and next >= 50:
				checkpoint = 1 / 2
			elif self.meters[state] < 33 and next >= 33:
				checkpoint = 1 / 3
			self.meters[state] = next
			self.meters[state] %= 100
			self.frameidx = floor(self.meters[state] * len(self.frames[self.state]) / 100)
		else:
			self.meters[state] = 0
			self.frameidx = 0
			self.state = state

		if loop or checkpoint != 1:
			draw(self.lanenum, self.pos, self.frames[self.state][self.frameidx])
		else:
			draw(self.lanenum, self.pos, self.frames[self.state][len(self.frames[self.state]) - 1])

		return checkpoint

	def explode(self):
		result = self.animate('explode', loop=False)
		if result == 1 / 3:
			for obj in lanes[self.lanenum]:
				if isinstance(obj, Unit):
					if (self.isplayer and not obj.isplayer and obj.hp > 0 and self.pos + self.aoe / 2 > obj.pos and self.pos - self.aoe / 2 < obj.pos) or (not obj.isplayer and obj.isplayer and obj.hp > 0 and self.pos + self.aoe / 2 > obj.pos and self.pos - self.aoe / 2 < obj.pos):
						obj.hp -= self.atk
						obj.state = 'hurt'
		elif result == 1:
			remove(self, lanes[self.lanenum])

	def run(self):
		#finishing exploding.
		if self.state == 'explode':
			self.explode()

		#reached max range.
		elif self.pos >= self.targetpos if self.isplayer else self.pos <= self.targetpos:
			if self.aoe:
				self.explode()
			else:
				remove(self, lanes[self.lanenum])

		#not reached max range.
		else:
			nextpos = self.pos + self.mspd if self.isplayer else self.pos - self.mspd
			self.animate('move')
			#reached a unit.
			for obj in lanes[self.lanenum]:
				if isinstance(obj, Unit):
					if (self.isplayer and not obj.isplayer and obj.hp > 0 and self.pos <= obj.pos and nextpos >= obj.pos) or (not self.isplayer and obj.isplayer and obj.hp > 0 and self.pos >= obj.pos and nextpos <= obj.pos):
						self.pos = obj.pos
						if self.aoe:
							self.explode()
						else:
							obj.hp -= self.atk
							if obj.state != 'attack':
								obj.state = 'hurt'
							remove(self, lanes[self.lanenum])
						return
			self.pos = nextpos

class SmallArrow(Missle):
	frames = extractframes({'move': r'\effects\smallarrow.png', 'explode': r'\effects\smallarrow.png'})
	mspd = 40
	aspd = 100
	def __init__(self, isplayer, lanenum, pos, targetpos, atk):
		super().__init__(mspd=SmallArrow.mspd, aspd=SmallArrow.aspd, atk=atk, frames=SmallArrow.frames, aoe=None, isplayer=isplayer, lanenum=lanenum, pos=pos, targetpos=targetpos)


class Arrow(Missle):
	frames = extractframes({'move': r'\effects\arrow.png', 'explode': r'\effects\arrow.png'})
	mspd = 40
	aspd = 100
	def __init__(self, isplayer, lanenum, pos, targetpos, atk):
		super().__init__(mspd=Arrow.mspd, aspd=Arrow.aspd, atk=atk, frames=Arrow.frames, aoe=None, isplayer=isplayer, lanenum=lanenum, pos=pos, targetpos=targetpos)

class Fireball(Missle):
	frames = extractframes({'move': r'\effects\blank.png', 'explode': r'\effects\fireball.gif'})
	mspd = 100
	aspd = 5
	def __init__(self, isplayer, lanenum, pos, targetpos, atk):
		super().__init__(mspd=Fireball.mspd, aspd=Fireball.aspd, atk=atk, frames=Fireball.frames, aoe=200, isplayer=isplayer, lanenum=lanenum, pos=pos, targetpos=targetpos)


class Team:
	def __init__(self, isplayer):
		self.spawnpts = 0
		self.spawnrate = .15
		self.boostcost = 20
		self.life = 100
		self.units = []
		self.unit = None
		self.isplayer = isplayer

	def deploy(self, lanenum):
		if self.unit is not None and self.unit.cost <= self.spawnpts:
			self.unit(lanenum, self.isplayer)
			self.spawnpts -= self.unit.cost

	def boost(self):
		if self.spawnpts >= self.boostcost:
			self.spawnpts -= self.boostcost
			self.spawnrate += self.spawnrate / 3
			self.boostcost = self.boostcost * 2

class Poring(Unit):
	frames = extractframes({'move': r'\monsters\rocky\poring08.gif', 'attack': r'\monsters\rocky\poring16.gif', 'hurt': r'\monsters\rocky\poring24.gif', 'die': r'\monsters\rocky\poring32.gif'})
	cost = 5
	hp = 10
	atk = 2
	range = 40
	mspd = 2
	aspd = 3
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Poring.frames, hp=Poring.hp, atk=Poring.atk, range=Poring.range, aspd=Poring.aspd, mspd=Poring.mspd, isplayer=isplayer, lanenum=lanenum)

class Poporing(Unit):
	frames = extractframes({'move': r'\monsters\rocky\poporing08.gif', 'attack': r'\monsters\rocky\poporing16.gif', 'hurt': r'\monsters\rocky\poporing24.gif', 'die': r'\monsters\rocky\poporing32.gif'})
	cost = 15
	hp = 25
	atk = 6
	range = 40
	mspd = 2
	aspd = 4
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Poporing.frames, hp=Poporing.hp, atk=Poporing.atk, range=Poporing.range, aspd=Poporing.aspd, mspd=Poporing.mspd, isplayer=isplayer, lanenum=lanenum)

class Pecopeco(Unit):
	frames = extractframes({'move': r'\monsters\rocky\pecopeco08.gif', 'attack': r'\monsters\rocky\pecopeco16.gif', 'hurt': r'\monsters\rocky\pecopeco24.gif', 'die': r'\monsters\rocky\pecopeco32.gif'})
	cost = 10
	hp = 20
	atk = 4
	range = 50
	mspd = 3
	aspd = 2.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Pecopeco.frames, hp=Pecopeco.hp, atk=Pecopeco.atk, range=Pecopeco.range, aspd=Pecopeco.aspd, mspd=Pecopeco.mspd, isplayer=isplayer, lanenum=lanenum)

class Frilldora(Unit):
	frames = extractframes({'move': r'\monsters\rocky\frilldora08.gif', 'attack': r'\monsters\rocky\frilldora16.gif', 'hurt': r'\monsters\rocky\frilldora24.gif', 'die': r'\monsters\rocky\frilldora32.gif'})
	cost = 18
	hp = 25
	atk = 8
	range = 50
	mspd = 3
	aspd = 3
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Frilldora.frames, hp=Frilldora.hp, atk=Frilldora.atk, range=Frilldora.range, aspd=Frilldora.aspd, mspd=Frilldora.mspd, isplayer=isplayer, lanenum=lanenum)

class Angeling(Unit):
	frames = extractframes({'move': r'\monsters\rocky\angeling08.gif', 'attack': r'\monsters\rocky\angeling16.gif', 'hurt': r'\monsters\rocky\angeling24.gif', 'die': r'\monsters\rocky\angeling32.gif'})
	cost = 40
	hp = 100
	atk = 5
	range = 50
	mspd = 4
	aspd = 3
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Angeling.frames, hp=Angeling.hp, atk=Angeling.atk, range=Angeling.range, aspd=Angeling.aspd, mspd=Angeling.mspd, isplayer=isplayer, lanenum=lanenum)

class AncientWorm(Unit):
	frames = extractframes({'move': r'\monsters\rocky\ancient_worm08.gif', 'attack': r'\monsters\rocky\ancient_worm16.gif', 'hurt': r'\monsters\rocky\ancient_worm24.gif', 'die': r'\monsters\rocky\ancient_worm32.gif'})
	cost = 25
	hp = 50
	atk = 15
	range = 50
	mspd = 2
	aspd = 4
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=AncientWorm.frames, hp=AncientWorm.hp, atk=AncientWorm.atk, range=AncientWorm.range, aspd=AncientWorm.aspd, mspd=AncientWorm.mspd, isplayer=isplayer, lanenum=lanenum)

class Petit(Unit):
	frames = extractframes({'move': r'\monsters\rocky\petit08.gif', 'attack': r'\monsters\rocky\petit16.gif', 'hurt': r'\monsters\rocky\petit24.gif', 'die': r'\monsters\rocky\petit32.gif'})
	cost = 20
	hp = 30
	atk = 11
	range = 50
	mspd = 2.5
	aspd = 3
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Petit.frames, hp=Petit.hp, atk=Petit.atk, range=Petit.range, aspd=Petit.aspd, mspd=Petit.mspd, isplayer=isplayer, lanenum=lanenum)

class FlyingPetit(Unit):
	frames = extractframes({'move': r'\monsters\rocky\petit_08.gif', 'attack': r'\monsters\rocky\petit_16.gif', 'hurt': r'\monsters\rocky\petit_24.gif', 'die': r'\monsters\rocky\petit_32.gif'})
	cost = 20
	hp = 25
	atk = 13
	range = 50
	mspd = 3
	aspd = 3
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=FlyingPetit.frames, hp=FlyingPetit.hp, atk=FlyingPetit.atk, range=FlyingPetit.range, aspd=FlyingPetit.aspd, mspd=FlyingPetit.mspd, isplayer=isplayer, lanenum=lanenum)

class Wormtail(Unit):
	frames = extractframes({'move': r'\monsters\rocky\worm_tail08.gif', 'attack': r'\monsters\rocky\worm_tail16.gif', 'hurt': r'\monsters\rocky\worm_tail24.gif', 'die': r'\monsters\rocky\worm_tail32.gif'})
	cost = 7
	hp = 14
	atk = 4.2
	range = 70
	mspd = 2
	aspd = 4
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Wormtail.frames, hp=Wormtail.hp, atk=Wormtail.atk, range=Wormtail.range, aspd=Wormtail.aspd, mspd=Wormtail.mspd, isplayer=isplayer, lanenum=lanenum)

class Sidewinder(Unit):
	frames = extractframes({'move': r'\monsters\rocky\side_winder08.gif', 'attack': r'\monsters\rocky\side_winder16.gif', 'hurt': r'\monsters\rocky\side_winder24.gif', 'die': r'\monsters\rocky\side_winder32.gif'})
	cost = 8
	hp = 15
	atk = 5
	range = 50
	mspd = 2
	aspd = 4
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Sidewinder.frames, hp=Sidewinder.hp, atk=Sidewinder.atk, range=Sidewinder.range, aspd=Sidewinder.aspd, mspd=Sidewinder.mspd, isplayer=isplayer, lanenum=lanenum)

class Flora(Unit):
	frames = extractframes({'move': r'\monsters\rocky\flora08.gif', 'attack': r'\monsters\rocky\flora16.gif', 'hurt': r'\monsters\rocky\flora24.gif', 'die': r'\monsters\rocky\flora32.gif'})
	cost = 15
	hp = 20
	atk = 8
	range = 70
	mspd = 5
	aspd = 6
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Flora.frames, hp=Flora.hp, atk=Flora.atk, range=Flora.range, aspd=Flora.aspd, mspd=Flora.mspd, isplayer=isplayer, lanenum=lanenum)
		self.pos = randint(LEFT_SIDE + 100, RIGHT_SIDE - 100)

	def move(self):
		self.animate('move')

class Skeggiold(Unit):
	frames = extractframes({'move': r'\monsters\rocky\skeggiold08.gif', 'attack': r'\monsters\rocky\skeggiold16.gif', 'hurt': r'\monsters\rocky\skeggiold24.gif', 'die': r'\monsters\rocky\skeggiold32.gif'})
	cost = 30
	hp = 40
	atk = 8
	range = 50
	mspd = 2.5
	aspd = 4
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Skeggiold.frames, hp=Skeggiold.hp, atk=Skeggiold.atk, range=Skeggiold.range, aspd=Skeggiold.aspd, mspd=Skeggiold.mspd, isplayer=isplayer, lanenum=lanenum)

class Alligator(Unit):
	frames = extractframes({'move': r'\monsters\beach\alligator08.gif', 'attack': r'\monsters\beach\alligator16.gif', 'hurt': r'\monsters\beach\alligator24.gif', 'die': r'\monsters\beach\alligator32.gif'})
	cost = 10
	hp = 20
	atk = 8
	range = 50
	mspd = 2.4
	aspd = 5.1
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Alligator.frames, hp=Alligator.hp, atk=Alligator.atk, range=Alligator.range, aspd=Alligator.aspd, mspd=Alligator.mspd, isplayer=isplayer, lanenum=lanenum)

class Ambernite(Unit):
	frames = extractframes({'move': r'\monsters\beach\ambernite08.gif', 'attack': r'\monsters\beach\ambernite16.gif', 'hurt': r'\monsters\beach\ambernite24.gif', 'die': r'\monsters\beach\ambernite32.gif'})
	cost = 6
	hp = 15
	atk = 4
	range = 50
	mspd = 2.5
	aspd = 3.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Ambernite.frames, hp=Ambernite.hp, atk=Ambernite.atk, range=Ambernite.range, aspd=Ambernite.aspd, mspd=Ambernite.mspd, isplayer=isplayer, lanenum=lanenum)

class Anolian(Unit):
	frames = extractframes({'move': r'\monsters\beach\anolian08.gif', 'attack': r'\monsters\beach\anolian16.gif', 'hurt': r'\monsters\beach\anolian24.gif', 'die': r'\monsters\beach\anolian32.gif'})
	cost = 18
	hp = 26
	atk = 5
	range = 50
	mspd = 3.5
	aspd = 6
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Anolian.frames, hp=Anolian.hp, atk=Anolian.atk, range=Anolian.range, aspd=Anolian.aspd, mspd=Anolian.mspd, isplayer=isplayer, lanenum=lanenum)

class Furseal(Unit):
	frames = extractframes({'move': r'\monsters\beach\fur_seal08.gif', 'attack': r'\monsters\beach\fur_seal16.gif', 'hurt': r'\monsters\beach\fur_seal24.gif', 'die': r'\monsters\beach\fur_seal32.gif'})
	cost = 15
	hp = 22
	atk = 6
	range = 50
	mspd = 3
	aspd = 4.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Furseal.frames, hp=Furseal.hp, atk=Furseal.atk, range=Furseal.range, aspd=Furseal.aspd, mspd=Furseal.mspd, isplayer=isplayer, lanenum=lanenum)

class Merman(Unit):
	frames = extractframes({'move': r'\monsters\beach\merman08.gif', 'attack': r'\monsters\beach\merman16.gif', 'hurt': r'\monsters\beach\merman24.gif', 'die': r'\monsters\beach\merman32.gif'})
	cost = 10
	hp = 20
	atk = 7
	range = 80
	mspd = 3.3
	aspd = 4.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Merman.frames, hp=Merman.hp, atk=Merman.atk, range=Merman.range, aspd=Merman.aspd, mspd=Merman.mspd, isplayer=isplayer, lanenum=lanenum)

class Mobster(Unit):
	frames = extractframes({'move': r'\monsters\beach\mobster08.gif', 'attack': r'\monsters\beach\mobster16.gif', 'hurt': r'\monsters\beach\mobster24.gif', 'die': r'\monsters\beach\mobster32.gif'})
	cost = 15
	hp = 30
	atk = 6
	range = 50
	mspd = 2.3
	aspd = 4.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Mobster.frames, hp=Mobster.hp, atk=Mobster.atk, range=Mobster.range, aspd=Mobster.aspd, mspd=Mobster.mspd, isplayer=isplayer, lanenum=lanenum)


class Penomena(Unit):
	frames = extractframes({'move': r'\monsters\beach\penomena08.gif', 'attack': r'\monsters\beach\penomena16.gif', 'hurt': r'\monsters\beach\penomena24.gif', 'die': r'\monsters\beach\penomena32.gif'})
	cost = 15
	hp = 25
	atk = 5.6
	range = 50
	mspd = 0.4
	aspd = 5.1
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Penomena.frames, hp=Penomena.hp, atk=Penomena.atk, range=Penomena.range, aspd=Penomena.aspd, mspd=Penomena.mspd, isplayer=isplayer, lanenum=lanenum)
		self.pos = randint(LEFT_SIDE + 100, RIGHT_SIDE - 100)

	def move(self):
		self.animate('move')

class Phen(Unit):
	frames = extractframes({'move': r'\monsters\beach\phen08.gif', 'attack': r'\monsters\beach\phen16.gif', 'hurt': r'\monsters\beach\phen24.gif', 'die': r'\monsters\beach\phen32.gif'})
	cost = 10
	hp = 15
	atk = 8
	range = 50
	mspd = 1.8
	aspd = 4.8
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Phen.frames, hp=Phen.hp, atk=Phen.atk, range=Phen.range, aspd=Phen.aspd, mspd=Phen.mspd, isplayer=isplayer, lanenum=lanenum)

class PirateSkeleton(Unit):
	frames = extractframes({'move': r'\monsters\beach\pirate_skel08.gif', 'attack': r'\monsters\beach\pirate_skel16.gif', 'hurt': r'\monsters\beach\pirate_skel24.gif', 'die': r'\monsters\beach\pirate_skel32.gif'})
	cost = 10
	hp = 20
	atk = 8
	range = 50
	mspd = 3.2
	aspd = 4.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=PirateSkeleton.frames, hp=PirateSkeleton.hp, atk=PirateSkeleton.atk, range=PirateSkeleton.range, aspd=PirateSkeleton.aspd, mspd=PirateSkeleton.mspd, isplayer=isplayer, lanenum=lanenum)

class Plankton(Unit):
	frames = extractframes({'move': r'\monsters\beach\plankton08.gif', 'attack': r'\monsters\beach\plankton16.gif', 'hurt': r'\monsters\beach\plankton24.gif', 'die': r'\monsters\beach\plankton32.gif'})
	cost = 7
	hp = 10
	atk = 4
	range = 50
	mspd = 1.3
	aspd = 4.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Plankton.frames, hp=Plankton.hp, atk=Plankton.atk, range=Plankton.range, aspd=Plankton.aspd, mspd=Plankton.mspd, isplayer=isplayer, lanenum=lanenum)


class Shellfish(Unit):
	frames = extractframes({'move': r'\monsters\beach\shellfish08.gif', 'attack': r'\monsters\beach\shellfish16.gif', 'hurt': r'\monsters\beach\shellfish24.gif', 'die': r'\monsters\beach\shellfish32.gif'})
	cost = 5
	hp = 12
	atk = 4
	range = 50
	mspd = 2.3
	aspd = 4.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Shellfish.frames, hp=Shellfish.hp, atk=Shellfish.atk, range=Shellfish.range, aspd=Shellfish.aspd, mspd=Shellfish.mspd, isplayer=isplayer, lanenum=lanenum)


class Acidus(Unit):
	frames = extractframes({'move': r'\monsters\cave\acidus08.gif', 'attack': r'\monsters\cave\acidus16.gif', 'hurt': r'\monsters\cave\acidus24.gif', 'die': r'\monsters\cave\acidus32.gif'})
	cost = 30
	hp = 45
	atk = 20
	range = 70
	mspd = 4
	aspd = 5.4
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Acidus.frames, hp=Acidus.hp, atk=Acidus.atk, range=Acidus.range, aspd=Acidus.aspd, mspd=Acidus.mspd, isplayer=isplayer, lanenum=lanenum)


class Acidus_(Unit):
	frames = extractframes({'move': r'\monsters\cave\acidus_08.gif', 'attack': r'\monsters\cave\acidus_16.gif', 'hurt': r'\monsters\cave\acidus_24.gif', 'die': r'\monsters\cave\acidus_32.gif'})
	cost = 30
	hp = 45
	atk = 15
	range = 70
	mspd = 4
	aspd = 5.4
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Acidus_.frames, hp=Acidus_.hp, atk=Acidus_.atk, range=Acidus_.range, aspd=Acidus_.aspd, mspd=Acidus_.mspd, isplayer=isplayer, lanenum=lanenum)

class AmMut(Unit):
	frames = extractframes({'move': r'\monsters\cave\am_mut08.gif', 'attack': r'\monsters\cave\am_mut16.gif', 'hurt': r'\monsters\cave\am_mut24.gif', 'die': r'\monsters\cave\am_mut32.gif'})
	cost = 15
	hp = 20
	atk = 10
	range = 50
	mspd = 2
	aspd = 5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=AmMut.frames, hp=AmMut.hp, atk=AmMut.atk, range=AmMut.range, aspd=AmMut.aspd, mspd=AmMut.mspd, isplayer=isplayer, lanenum=lanenum)

class Andre(Unit):
	frames = extractframes({'move': r'\monsters\cave\andre08.gif', 'attack': r'\monsters\cave\andre16.gif', 'hurt': r'\monsters\cave\andre24.gif', 'die': r'\monsters\cave\andre32.gif'})
	cost = 5
	hp = 12
	atk = 4
	range = 50
	mspd = 3
	aspd = 3.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Andre.frames, hp=Andre.hp, atk=Andre.atk, range=Andre.range, aspd=Andre.aspd, mspd=Andre.mspd, isplayer=isplayer, lanenum=lanenum)

class AntEgg(Unit):
	frames = extractframes({'move': r'\monsters\cave\ant_egg08.gif', 'attack': r'\monsters\cave\ant_egg16.gif', 'hurt': r'\monsters\cave\ant_egg24.gif', 'die': r'\monsters\cave\ant_egg32.gif'})
	cost = 10
	hp = 30
	atk = 0
	range = 0
	mspd = 0
	aspd = 0
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=AntEgg.frames, hp=AntEgg.hp, atk=AntEgg.atk, range=AntEgg.range, aspd=AntEgg.aspd, mspd=AntEgg.mspd, isplayer=isplayer, lanenum=lanenum)
		self.pos = randint(LEFT_SIDE + 100, RIGHT_SIDE - 100)

	def move(self):
		self.animate('move')


class Crystal(Unit):
	frames = extractframes({'move': r'\monsters\cave\crystal_108.gif', 'attack': r'\monsters\cave\crystal_116.gif', 'hurt': r'\monsters\cave\crystal_124.gif', 'die': r'\monsters\cave\crystal_132.gif'})
	cost = 20
	hp = 33
	atk = 10
	range = 50
	mspd = 2.5
	aspd = 4
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Crystal.frames, hp=Crystal.hp, atk=Crystal.atk, range=Crystal.range, aspd=Crystal.aspd, mspd=Crystal.mspd, isplayer=isplayer, lanenum=lanenum)

class Freezer(Unit):
	frames = extractframes({'move': r'\monsters\cave\freezer08.gif', 'attack': r'\monsters\cave\freezer16.gif', 'hurt': r'\monsters\cave\freezer24.gif', 'die': r'\monsters\cave\freezer32.gif'})
	cost = 17
	hp = 35
	atk = 10
	range = 50
	mspd = 1.4
	aspd = 3
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Freezer.frames, hp=Freezer.hp, atk=Freezer.atk, range=Freezer.range, aspd=Freezer.aspd, mspd=Freezer.mspd, isplayer=isplayer, lanenum=lanenum)

class Lava_Golem(Unit):
	frames = extractframes({'move': r'\monsters\cave\lava_golem08.gif', 'attack': r'\monsters\cave\lava_golem16.gif', 'hurt': r'\monsters\cave\lava_golem24.gif', 'die': r'\monsters\cave\lava_golem32.gif'})
	cost = 25
	hp = 55
	atk = 15
	range = 50
	mspd = 1.5
	aspd = 3
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Lava_Golem.frames, hp=Lava_Golem.hp, atk=Lava_Golem.atk, range=Lava_Golem.range, aspd=Lava_Golem.aspd, mspd=Lava_Golem.mspd, isplayer=isplayer, lanenum=lanenum)

class Maya(Unit):
	frames = extractframes({'move': r'\monsters\cave\maya08.gif', 'attack': r'\monsters\cave\maya16.gif', 'hurt': r'\monsters\cave\maya24.gif', 'die': r'\monsters\cave\maya32.gif'})
	cost = 40
	hp = 100
	atk = 10
	range = 50
	mspd = 1.5
	aspd = 5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Maya.frames, hp=Maya.hp, atk=Maya.atk, range=Maya.range, aspd=Maya.aspd, mspd=Maya.mspd, isplayer=isplayer, lanenum=lanenum)


class Phreeoni(Unit):
	frames = extractframes({'move': r'\monsters\cave\phreeoni08.gif', 'attack': r'\monsters\cave\phreeoni16.gif', 'hurt': r'\monsters\cave\phreeoni24.gif', 'die': r'\monsters\cave\phreeoni32.gif'})
	cost = 40
	hp = 100
	atk = 10
	range = 50
	mspd = 1
	aspd = 5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Phreeoni.frames, hp=Phreeoni.hp, atk=Phreeoni.atk, range=Phreeoni.range, aspd=Phreeoni.aspd, mspd=Phreeoni.mspd, isplayer=isplayer, lanenum=lanenum)

class Piere(Unit):
	frames = extractframes({'move': r'\monsters\cave\piere08.gif', 'attack': r'\monsters\cave\piere16.gif', 'hurt': r'\monsters\cave\piere24.gif', 'die': r'\monsters\cave\piere32.gif'})
	cost = 6
	hp = 12
	atk = 4
	range = 50
	mspd = 3.3
	aspd = 3.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Piere.frames, hp=Piere.hp, atk=Piere.atk, range=Piere.range, aspd=Piere.aspd, mspd=Piere.mspd, isplayer=isplayer, lanenum=lanenum)

class Pitman(Unit):
	frames = extractframes({'move': r'\monsters\cave\pitman08.gif', 'attack': r'\monsters\cave\pitman16.gif', 'hurt': r'\monsters\cave\pitman24.gif', 'die': r'\monsters\cave\pitman32.gif'})
	cost = 15
	hp = 20
	atk = 7
	range = 50
	mspd = 1.5
	aspd = 4
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Pitman.frames, hp=Pitman.hp, atk=Pitman.atk, range=Pitman.range, aspd=Pitman.aspd, mspd=Pitman.mspd, isplayer=isplayer, lanenum=lanenum)

class Shelter(Unit):
	frames = extractframes({'move': r'\monsters\cave\shelter08.gif', 'attack': r'\monsters\cave\shelter16.gif', 'hurt': r'\monsters\cave\shelter24.gif', 'die': r'\monsters\cave\shelter32.gif'})
	cost = 25
	hp = 66
	atk = 12
	range = 70
	mspd = 2.7
	aspd = 5.8
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Shelter.frames, hp=Shelter.hp, atk=Shelter.atk, range=Shelter.range, aspd=Shelter.aspd, mspd=Shelter.mspd, isplayer=isplayer, lanenum=lanenum)

class Zenorc(Unit):
	frames = extractframes({'move': r'\monsters\cave\zenorc08.gif', 'attack': r'\monsters\cave\zenorc16.gif', 'hurt': r'\monsters\cave\zenorc24.gif', 'die': r'\monsters\cave\zenorc32.gif'})
	cost = 16
	hp = 28
	atk = 5
	range = 40
	mspd = 2.5
	aspd = 6.2
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Zenorc.frames, hp=Zenorc.hp, atk=Zenorc.atk, range=Zenorc.range, aspd=Zenorc.aspd, mspd=Zenorc.mspd, isplayer=isplayer, lanenum=lanenum)

class ZipperBear(Unit):
	frames = extractframes({'move': r'\monsters\cave\zipper_bear08.gif', 'attack': r'\monsters\cave\zipper_bear16.gif', 'hurt': r'\monsters\cave\zipper_bear24.gif', 'die': r'\monsters\cave\zipper_bear32.gif'})
	cost = 14
	hp = 27
	atk = 5
	range = 50
	mspd = 2.3
	aspd = 6
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=ZipperBear.frames, hp=ZipperBear.hp, atk=ZipperBear.atk, range=ZipperBear.range, aspd=ZipperBear.aspd, mspd=ZipperBear.mspd, isplayer=isplayer, lanenum=lanenum)

class Zombie_master(Unit):
	frames = extractframes({'move': r'\monsters\cave\zombie_master08.gif', 'attack': r'\monsters\cave\zombie_master16.gif', 'hurt': r'\monsters\cave\zombie_master24.gif', 'die': r'\monsters\cave\zombie_master32.gif'})
	cost = 20
	hp = 44
	atk = 7
	range = 50
	mspd = 2
	aspd = 3
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Zombie_master.frames, hp=Zombie_master.hp, atk=Zombie_master.atk, range=Zombie_master.range, aspd=Zombie_master.aspd, mspd=Zombie_master.mspd, isplayer=isplayer, lanenum=lanenum)

class Zombie_prisoner(Unit):
	frames = extractframes({'move': r'\monsters\cave\zombie_prisoner08.gif', 'attack': r'\monsters\cave\zombie_prisoner16.gif', 'hurt': r'\monsters\cave\zombie_prisoner24.gif', 'die': r'\monsters\cave\zombie_prisoner32.gif'})
	cost = 12
	hp = 22
	atk = 4
	range = 50
	mspd = 1
	aspd = 3
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Zombie_prisoner.frames, hp=Zombie_prisoner.hp, atk=Zombie_prisoner.atk, range=Zombie_prisoner.range, aspd=Zombie_prisoner.aspd, mspd=Zombie_prisoner.mspd, isplayer=isplayer, lanenum=lanenum)

class Zombie(Unit):
	frames = extractframes({'move': r'\monsters\cave\zombie08.gif', 'attack': r'\monsters\cave\zombie16.gif', 'hurt': r'\monsters\cave\zombie24.gif', 'die': r'\monsters\cave\zombie32.gif'})
	cost = 7
	hp = 10
	atk = 3.6
	range = 50
	mspd = 1.5
	aspd = 3
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Zombie.frames, hp=Zombie.hp, atk=Zombie.atk, range=Zombie.range, aspd=Zombie.aspd, mspd=Zombie.mspd, isplayer=isplayer, lanenum=lanenum)

class Orc_zombie(Unit):
	frames = extractframes({'move': r'\monsters\cave\orc_zombie08.gif', 'attack': r'\monsters\cave\orc_zombie16.gif', 'hurt': r'\monsters\cave\orc_zombie24.gif', 'die': r'\monsters\cave\orc_zombie32.gif'})
	cost = 10
	hp = 15
	atk = 5
	range = 50
	mspd = 1.6
	aspd = 3.3
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Orc_zombie.frames, hp=Orc_zombie.hp, atk=Orc_zombie.atk, range=Orc_zombie.range, aspd=Orc_zombie.aspd, mspd=Orc_zombie.mspd, isplayer=isplayer, lanenum=lanenum)

class Nine_tail(Unit):
	frames = extractframes({'move': r'\monsters\forest\nine_tail08.gif', 'attack': r'\monsters\forest\nine_tail16.gif', 'hurt': r'\monsters\forest\nine_tail24.gif', 'die': r'\monsters\forest\nine_tail32.gif'})
	cost = 14
	hp = 35
	atk = 8
	range = 60
	mspd = 3.2
	aspd = 6
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Nine_tail.frames, hp=Nine_tail.hp, atk=Nine_tail.atk, range=Nine_tail.range, aspd=Nine_tail.aspd, mspd=Nine_tail.mspd, isplayer=isplayer, lanenum=lanenum)


class Orc_archer(Unit):
	frames = extractframes({'move': r'\monsters\forest\orc_archer08.gif', 'attack': r'\monsters\forest\orc_archer16.gif', 'hurt': r'\monsters\forest\orc_archer24.gif', 'die': r'\monsters\forest\orc_archer32.gif'})
	cost = 15
	hp = 29
	atk = 7
	range = 220
	mspd = 2
	aspd = 6
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Orc_archer.frames, hp=Orc_archer.hp, atk=Orc_archer.atk, range=Orc_archer.range, aspd=Orc_archer.aspd, mspd=Orc_archer.mspd, isplayer=isplayer, lanenum=lanenum, missle=Arrow)

class Orc_baby(Unit):
	frames = extractframes({'move': r'\monsters\forest\orc_baby08.gif', 'attack': r'\monsters\forest\orc_baby16.gif', 'hurt': r'\monsters\forest\orc_baby24.gif', 'die': r'\monsters\forest\orc_baby32.gif'})
	cost = 15
	hp = 14
	atk = 5
	range = 50
	mspd = 2.5
	aspd = 5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Orc_baby.frames, hp=Orc_baby.hp, atk=Orc_baby.atk, range=Orc_baby.range, aspd=Orc_baby.aspd, mspd=Orc_baby.mspd, isplayer=isplayer, lanenum=lanenum)

class Orc_lady(Unit):
	frames = extractframes({'move': r'\monsters\forest\orc_lady08.gif', 'attack': r'\monsters\forest\orc_lady16.gif', 'hurt': r'\monsters\forest\orc_lady24.gif', 'die': r'\monsters\forest\orc_lady32.gif'})
	cost = 14
	hp = 20
	atk = 7
	range = 50
	mspd = 2.5
	aspd = 6
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Orc_lady.frames, hp=Orc_lady.hp, atk=Orc_lady.atk, range=Orc_lady.range, aspd=Orc_lady.aspd, mspd=Orc_lady.mspd, isplayer=isplayer, lanenum=lanenum)

class Ork_hero(Unit):
	frames = extractframes({'move': r'\monsters\forest\ork_hero08.gif', 'attack': r'\monsters\forest\ork_hero16.gif', 'hurt': r'\monsters\forest\ork_hero24.gif', 'die': r'\monsters\forest\ork_hero32.gif'})
	cost = 40
	hp = 150
	atk = 7
	range = 50
	mspd = 1
	aspd = 6
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Ork_hero.frames, hp=Ork_hero.hp, atk=Ork_hero.atk, range=Ork_hero.range, aspd=Ork_hero.aspd, mspd=Ork_hero.mspd, isplayer=isplayer, lanenum=lanenum)

class Ork_warrior(Unit):
	frames = extractframes({'move': r'\monsters\forest\ork_warrior08.gif', 'attack': r'\monsters\forest\ork_warrior16.gif', 'hurt': r'\monsters\forest\ork_warrior24.gif', 'die': r'\monsters\forest\ork_warrior32.gif'})
	cost = 15
	hp = 20
	atk = 5
	range = 50
	mspd = 2.5
	aspd = 5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Ork_warrior.frames, hp=Ork_warrior.hp, atk=Ork_warrior.atk, range=Ork_warrior.range, aspd=Ork_warrior.aspd, mspd=Ork_warrior.mspd, isplayer=isplayer, lanenum=lanenum)

class Permeter(Unit):
	frames = extractframes({'move': r'\monsters\forest\permeter08.gif', 'attack': r'\monsters\forest\permeter16.gif', 'hurt': r'\monsters\forest\permeter24.gif', 'die': r'\monsters\forest\permeter32.gif'})
	cost = 18
	hp = 55
	atk = 5.6
	range = 50
	mspd = 1.5
	aspd = 4.2
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Permeter.frames, hp=Permeter.hp, atk=Permeter.atk, range=Permeter.range, aspd=Permeter.aspd, mspd=Permeter.mspd, isplayer=isplayer, lanenum=lanenum)

class Pest(Unit):
	frames = extractframes({'move': r'\monsters\forest\pest08.gif', 'attack': r'\monsters\forest\pest16.gif', 'hurt': r'\monsters\forest\pest24.gif', 'die': r'\monsters\forest\pest32.gif'})
	cost = 10
	hp = 20
	atk = 5
	range = 50
	mspd = 1.7
	aspd = 7
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Pest.frames, hp=Pest.hp, atk=Pest.atk, range=Pest.range, aspd=Pest.aspd, mspd=Pest.mspd, isplayer=isplayer, lanenum=lanenum)

class Spring_rabbit(Unit):
	frames = extractframes({'move': r'\monsters\forest\spring_rabbit08.gif', 'attack': r'\monsters\forest\spring_rabbit16.gif', 'hurt': r'\monsters\forest\spring_rabbit24.gif', 'die': r'\monsters\forest\spring_rabbit32.gif'})
	cost = 18
	hp = 30
	atk = 5.5
	range = 50
	mspd = 3
	aspd = 6
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Spring_rabbit.frames, hp=Spring_rabbit.hp, atk=Spring_rabbit.atk, range=Spring_rabbit.range, aspd=Spring_rabbit.aspd, mspd=Spring_rabbit.mspd, isplayer=isplayer, lanenum=lanenum)

class Willow(Unit):
	frames = extractframes({'move': r'\monsters\forest\willow08.gif', 'attack': r'\monsters\forest\willow16.gif', 'hurt': r'\monsters\forest\willow24.gif', 'die': r'\monsters\forest\willow32.gif'})
	cost = 5
	hp = 15
	atk = 3.5
	range = 50
	mspd = 1.5
	aspd = 5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Willow.frames, hp=Willow.hp, atk=Willow.atk, range=Willow.range, aspd=Willow.aspd, mspd=Willow.mspd, isplayer=isplayer, lanenum=lanenum)

class Wolf(Unit):
	frames = extractframes({'move': r'\monsters\forest\wolf08.gif', 'attack': r'\monsters\forest\wolf16.gif', 'hurt': r'\monsters\forest\wolf24.gif', 'die': r'\monsters\forest\wolf32.gif'})
	cost = 10
	hp = 18
	atk = 4
	range = 50
	mspd = 3.1
	aspd = 5.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Wolf.frames, hp=Wolf.hp, atk=Wolf.atk, range=Wolf.range, aspd=Wolf.aspd, mspd=Wolf.mspd, isplayer=isplayer, lanenum=lanenum)

class Wooden_golem(Unit):
	frames = extractframes({'move': r'\monsters\forest\wooden_golem08.gif', 'attack': r'\monsters\forest\wooden_golem16.gif', 'hurt': r'\monsters\forest\wooden_golem24.gif', 'die': r'\monsters\forest\wooden_golem32.gif'})
	cost = 20
	hp = 77
	atk = 8
	range = 50
	mspd = 1.5
	aspd = 3.2
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Wooden_golem.frames, hp=Wooden_golem.hp, atk=Wooden_golem.atk, range=Wooden_golem.range, aspd=Wooden_golem.aspd, mspd=Wooden_golem.mspd, isplayer=isplayer, lanenum=lanenum)

# class Wootan_fighter(Unit):
# 	frames = extractframes({'move': r'\monsters\forest\wootan_fighter08.gif', 'attack': r'\monsters\forest\wootan_fighter16.gif', 'hurt': r'\monsters\forest\wootan_fighter24.gif', 'die': r'\monsters\forest\wootan_fighter32.gif'})
# 	cost = 20
# 	hp = 66
# 	atk = 8
# 	range = 50
# 	mspd = 2.9
# 	aspd = 4.2
# 	level = 1
# 	def __init__(self, lanenum, isplayer):
# 		super().__init__(frames=Wootan_fighter.frames, hp=Wootan_fighter.hp, atk=Wootan_fighter.atk, range=Wootan_fighter.range, aspd=Wootan_fighter.aspd, mspd=Wootan_fighter.mspd, isplayer=isplayer, lanenum=lanenum)

class Yoyo(Unit):
	frames = extractframes({'move': r'\monsters\forest\wootan_fighter08.gif', 'attack': r'\monsters\forest\wootan_fighter16.gif', 'hurt': r'\monsters\forest\wootan_fighter24.gif', 'die': r'\monsters\forest\wootan_fighter32.gif'})
	cost = 8
	hp = 15
	atk = 5.1
	range = 50
	mspd = 2.6
	aspd = 4
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Yoyo.frames, hp=Yoyo.hp, atk=Yoyo.atk, range=Yoyo.range, aspd=Yoyo.aspd, mspd=Yoyo.mspd, isplayer=isplayer, lanenum=lanenum)

class Wootan_shooter(Unit):
	frames = extractframes({'move': r'\monsters\forest\wootan_shooter08.gif', 'attack': r'\monsters\forest\wootan_shooter16.gif', 'hurt': r'\monsters\forest\wootan_shooter24.gif', 'die': r'\monsters\forest\wootan_shooter32.gif'})
	cost = 17
	hp = 50
	atk = 4
	range = 200
	mspd = 3
	aspd = 5.1
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Wootan_shooter.frames, hp=Wootan_shooter.hp, atk=Wootan_shooter.atk, range=Wootan_shooter.range, aspd=Wootan_shooter.aspd, mspd=Wootan_shooter.mspd, isplayer=isplayer, lanenum=lanenum)

class Alarm(Unit):
	frames = extractframes({'move': r'\monsters\grave\Alarm08.gif', 'attack': r'\monsters\grave\alarm16.gif', 'hurt': r'\monsters\grave\alarm24.gif', 'die': r'\monsters\grave\alarm32.gif'})
	cost = 20
	hp = 26
	atk = 7
	range = 50
	mspd = 3.1
	aspd = 6
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Alarm.frames, hp=Alarm.hp, atk=Alarm.atk, range=Alarm.range, aspd=Alarm.aspd, mspd=Alarm.mspd, isplayer=isplayer, lanenum=lanenum)

class Anacondaq(Unit):
	frames = extractframes({'move': r'\monsters\desert\anacondaq08.gif', 'attack': r'\monsters\desert\anacondaq16.gif', 'hurt': r'\monsters\desert\anacondaq24.gif', 'die': r'\monsters\desert\anacondaq32.gif'})
	cost = 5
	hp = 18
	atk = 2
	range = 40
	mspd = 2.5
	aspd = 4
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Anacondaq.frames, hp=Anacondaq.hp, atk=Anacondaq.atk, range=Anacondaq.range, aspd=Anacondaq.aspd, mspd=Anacondaq.mspd, isplayer=isplayer, lanenum=lanenum)

class Ancient_mimic(Unit):
	frames = extractframes({'move': r'\monsters\desert\ancient_mimic08.gif', 'attack': r'\monsters\desert\ancient_mimic16.gif', 'hurt': r'\monsters\desert\ancient_mimic24.gif', 'die': r'\monsters\desert\ancient_mimic32.gif'})
	cost = 18
	hp = 55
	atk = 5
	range = 70
	mspd = 1.5
	aspd = 5.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Ancient_mimic.frames, hp=Ancient_mimic.hp, atk=Ancient_mimic.atk, range=Ancient_mimic.range, aspd=Ancient_mimic.aspd, mspd=Ancient_mimic.mspd, isplayer=isplayer, lanenum=lanenum)

class Ancient_mummy(Unit):
	frames = extractframes({'move': r'\monsters\desert\ancient_mummy08.gif', 'attack': r'\monsters\desert\ancient_mummy16.gif', 'hurt': r'\monsters\desert\ancient_mummy24.gif', 'die': r'\monsters\desert\ancient_mummy32.gif'})
	cost = 20
	hp = 28
	atk = 5
	range = 50
	mspd = 1
	aspd = 3.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Ancient_mummy.frames, hp=Ancient_mummy.hp, atk=Ancient_mummy.atk, range=Ancient_mummy.range, aspd=Ancient_mummy.aspd, mspd=Ancient_mummy.mspd, isplayer=isplayer, lanenum=lanenum)

class Condor(Unit):
	frames = extractframes({'move': r'\monsters\desert\condor08.gif', 'attack': r'\monsters\desert\condor16.gif', 'hurt': r'\monsters\desert\condor24.gif', 'die': r'\monsters\desert\condor32.gif'})
	cost = 5
	hp = 10
	atk = 2
	range = 50
	mspd = 2.7
	aspd = 4
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Condor.frames, hp=Condor.hp, atk=Condor.atk, range=Condor.range, aspd=Condor.aspd, mspd=Condor.mspd, isplayer=isplayer, lanenum=lanenum)

class Desert_wolf(Unit):
	frames = extractframes({'move': r'\monsters\desert\desert_wolf08.gif', 'attack': r'\monsters\desert\desert_wolf16.gif', 'hurt': r'\monsters\desert\desert_wolf24.gif', 'die': r'\monsters\desert\desert_wolf32.gif'})
	cost = 15
	hp = 33
	atk = 6.2
	range = 50
	mspd = 3.2
	aspd = 3.8
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Desert_wolf.frames, hp=Desert_wolf.hp, atk=Desert_wolf.atk, range=Desert_wolf.range, aspd=Desert_wolf.aspd, mspd=Desert_wolf.mspd, isplayer=isplayer, lanenum=lanenum)

class Dragon_fly(Unit):
	frames = extractframes({'move': r'\monsters\desert\dragon_fly08.gif', 'attack': r'\monsters\desert\dragon_fly16.gif', 'hurt': r'\monsters\desert\dragon_fly24.gif', 'die': r'\monsters\desert\dragon_fly32.gif'})
	cost = 10
	hp = 12
	atk = 3
	range = 40
	mspd = 2.3
	aspd = 4.8
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Dragon_fly.frames, hp=Dragon_fly.hp, atk=Dragon_fly.atk, range=Dragon_fly.range, aspd=Dragon_fly.aspd, mspd=Dragon_fly.mspd, isplayer=isplayer, lanenum=lanenum)

class Kobold_archer(Unit):
	frames = extractframes({'move': r'\monsters\desert\kobold_archer08.gif', 'attack': r'\monsters\desert\kobold_archer16.gif', 'hurt': r'\monsters\desert\kobold_archer24.gif', 'die': r'\monsters\desert\kobold_archer32.gif'})
	cost = 10
	hp = 14
	atk = 6
	range = 180
	mspd = 2.5
	aspd = 6.2
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Kobold_archer.frames, hp=Kobold_archer.hp, atk=Kobold_archer.atk, range=Kobold_archer.range, aspd=Kobold_archer.aspd, mspd=Kobold_archer.mspd, isplayer=isplayer, lanenum=lanenum, missle=SmallArrow)

class Pasana(Unit):
	frames = extractframes({'move': r'\monsters\desert\pasana08.gif', 'attack': r'\monsters\desert\pasana16.gif', 'hurt': r'\monsters\desert\pasana24.gif', 'die': r'\monsters\desert\pasana32.gif'})
	cost = 18
	hp = 24
	atk = 4
	range = 50
	mspd = 2
	aspd = 4.2
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Pasana.frames, hp=Pasana.hp, atk=Pasana.atk, range=Pasana.range, aspd=Pasana.aspd, mspd=Pasana.mspd, isplayer=isplayer, lanenum=lanenum)

class Pharaoh(Unit):
	frames = extractframes({'move': r'\monsters\desert\pharaoh08.gif', 'attack': r'\monsters\desert\pharaoh16.gif', 'hurt': r'\monsters\desert\pharaoh24.gif', 'die': r'\monsters\desert\pharaoh32.gif'})
	cost = 40
	hp = 100
	atk = 4
	range = 50
	mspd = 1.2
	aspd = 3.1
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Pharaoh.frames, hp=Pharaoh.hp, atk=Pharaoh.atk, range=Pharaoh.range, aspd=Pharaoh.aspd, mspd=Pharaoh.mspd, isplayer=isplayer, lanenum=lanenum)

class Picky(Unit):
	frames = extractframes({'move': r'\monsters\desert\picky08.gif', 'attack': r'\monsters\desert\picky16.gif', 'hurt': r'\monsters\desert\picky24.gif', 'die': r'\monsters\desert\picky32.gif'})
	cost = 5
	hp = 8
	atk = 3
	range = 40
	mspd = 2.4
	aspd = 4.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Picky.frames, hp=Picky.hp, atk=Picky.atk, range=Picky.range, aspd=Picky.aspd, mspd=Picky.mspd, isplayer=isplayer, lanenum=lanenum)

class Zerom(Unit):
	frames = extractframes({'move': r'\monsters\desert\zerom08.gif', 'attack': r'\monsters\desert\zerom16.gif', 'hurt': r'\monsters\desert\zerom24.gif', 'die': r'\monsters\desert\zerom32.gif'})
	cost = 10
	hp = 18
	atk = 4
	range = 40
	mspd = 2.2
	aspd = 5.2
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Zerom.frames, hp=Zerom.hp, atk=Zerom.atk, range=Zerom.range, aspd=Zerom.aspd, mspd=Zerom.mspd, isplayer=isplayer, lanenum=lanenum)

class Alice(Unit):
	frames = extractframes({'move': r'\monsters\grave\Alice08.gif', 'attack': r'\monsters\grave\alice16.gif', 'hurt': r'\monsters\grave\alice24.gif', 'die': r'\monsters\grave\alice32.gif'})
	cost = 17
	hp = 25
	atk = 7
	range = 50
	mspd = 2.5
	aspd = 4.5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Alice.frames, hp=Alice.hp, atk=Alice.atk, range=Alice.range, aspd=Alice.aspd, mspd=Alice.mspd, isplayer=isplayer, lanenum=lanenum)

class Alicel(Unit):
	frames = extractframes({'move': r'\monsters\grave\Alicel08.gif', 'attack': r'\monsters\grave\alicel16.gif', 'hurt': r'\monsters\grave\alicel24.gif', 'die': r'\monsters\grave\alicel32.gif'})
	cost = 18
	hp = 28
	atk = 7
	range = 50
	mspd = 3.1
	aspd = 5.7
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Alicel.frames, hp=Alicel.hp, atk=Alicel.atk, range=Alicel.range, aspd=Alicel.aspd, mspd=Alicel.mspd, isplayer=isplayer, lanenum=lanenum)


class Aliot(Unit):
	frames = extractframes({'move': r'\monsters\grave\Aliot08.gif', 'attack': r'\monsters\grave\aliot16.gif', 'hurt': r'\monsters\grave\aliot24.gif', 'die': r'\monsters\grave\aliot32.gif'})
	cost = 22
	hp = 30
	atk = 7
	range = 50
	mspd = 3
	aspd = 5.8
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Aliot.frames, hp=Aliot.hp, atk=Aliot.atk, range=Aliot.range, aspd=Aliot.aspd, mspd=Aliot.mspd, isplayer=isplayer, lanenum=lanenum)


class Antique_firelock(Unit):
	frames = extractframes({'move': r'\monsters\grave\Antique_firelock08.gif', 'attack': r'\monsters\grave\antique_firelock16.gif', 'hurt': r'\monsters\grave\antique_firelock24.gif', 'die': r'\monsters\grave\antique_firelock32.gif'})
	cost = 25
	hp = 18
	atk = 12
	range = 50
	mspd = 2.3
	aspd = 4
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Antique_firelock.frames, hp=Antique_firelock.hp, atk=Antique_firelock.atk, range=Antique_firelock.range, aspd=Antique_firelock.aspd, mspd=Antique_firelock.mspd, isplayer=isplayer, lanenum=lanenum)

class Frus(Unit):
	frames = extractframes({'move': r'\monsters\grave\Frus08.gif', 'attack': r'\monsters\grave\frus16.gif', 'hurt': r'\monsters\grave\frus24.gif', 'die': r'\monsters\grave\frus32.gif'})
	cost = 17
	hp = 30
	atk = 8
	range = 70
	mspd = 3
	aspd = 5.2
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Frus.frames, hp=Frus.hp, atk=Frus.atk, range=Frus.range, aspd=Frus.aspd, mspd=Frus.mspd, isplayer=isplayer, lanenum=lanenum)

class Ghostring(Unit):
	frames = extractframes({'move': r'\monsters\grave\Ghostring08.gif', 'attack': r'\monsters\grave\ghostring16.gif', 'hurt': r'\monsters\grave\ghostring24.gif', 'die': r'\monsters\grave\ghostring32.gif'})
	cost = 40
	hp = 100
	atk = 12
	range = 50
	mspd = 3
	aspd = 3
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Ghostring.frames, hp=Ghostring.hp, atk=Ghostring.atk, range=Ghostring.range, aspd=Ghostring.aspd, mspd=Ghostring.mspd, isplayer=isplayer, lanenum=lanenum)

class Hyegun(Unit):
	frames = extractframes({'move': r'\monsters\grave\Hyegun08.gif', 'attack': r'\monsters\grave\hyegun16.gif', 'hurt': r'\monsters\grave\hyegun24.gif', 'die': r'\monsters\grave\hyegun32.gif'})
	cost = 17
	hp = 40
	atk = 6
	range = 50
	mspd = 3
	aspd = 5.7
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Hyegun.frames, hp=Hyegun.hp, atk=Hyegun.atk, range=Hyegun.range, aspd=Hyegun.aspd, mspd=Hyegun.mspd, isplayer=isplayer, lanenum=lanenum)

class Miyabi_ningyo(Unit):
	frames = extractframes({'move': r'\monsters\grave\Miyabi_ningyo08.gif', 'attack': r'\monsters\grave\miyabi_ningyo16.gif', 'hurt': r'\monsters\grave\miyabi_ningyo24.gif', 'die': r'\monsters\grave\miyabi_ningyo32.gif'})
	cost = 14
	hp = 20
	atk = 4
	range = 50
	mspd = 2.3
	aspd = 5
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Miyabi_ningyo.frames, hp=Miyabi_ningyo.hp, atk=Miyabi_ningyo.atk, range=Miyabi_ningyo.range, aspd=Miyabi_ningyo.aspd, mspd=Miyabi_ningyo.mspd, isplayer=isplayer, lanenum=lanenum)

class Munak(Unit):
	frames = extractframes({'move': r'\monsters\grave\Munak08.gif', 'attack': r'\monsters\grave\munak16.gif', 'hurt': r'\monsters\grave\munak24.gif', 'die': r'\monsters\grave\munak32.gif'})
	cost = 13
	hp = 22
	atk = 6.3
	range = 50
	mspd = 2
	aspd = 5.1
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Munak.frames, hp=Munak.hp, atk=Munak.atk, range=Munak.range, aspd=Munak.aspd, mspd=Munak.mspd, isplayer=isplayer, lanenum=lanenum)

class Myst(Unit):
	frames = extractframes({'move': r'\monsters\grave\Myst08.gif', 'attack': r'\monsters\grave\myst16.gif', 'hurt': r'\monsters\grave\myst24.gif', 'die': r'\monsters\grave\myst32.gif'})
	cost = 17
	hp = 24
	atk = 7.2
	range = 50
	mspd = 3
	aspd = 5.8
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Myst.frames, hp=Myst.hp, atk=Myst.atk, range=Myst.range, aspd=Myst.aspd, mspd=Myst.mspd, isplayer=isplayer, lanenum=lanenum)

class Owl_baron(Unit):
	frames = extractframes({'move': r'\monsters\grave\Owl_baron08.gif', 'attack': r'\monsters\grave\owl_baron16.gif', 'hurt': r'\monsters\grave\owl_baron24.gif', 'die': r'\monsters\grave\owl_baron32.gif'})
	cost = 30
	hp = 34
	atk = 12
	range = 60
	mspd = 3
	aspd = 5.1
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Owl_baron.frames, hp=Owl_baron.hp, atk=Owl_baron.atk, range=Owl_baron.range, aspd=Owl_baron.aspd, mspd=Owl_baron.mspd, isplayer=isplayer, lanenum=lanenum)

class Owl_duke(Unit):
	frames = extractframes({'move': r'\monsters\grave\Owl_duke08.gif', 'attack': r'\monsters\grave\owl_duke16.gif', 'hurt': r'\monsters\grave\owl_duke24.gif', 'die': r'\monsters\grave\owl_duke32.gif'})
	cost = 22
	hp = 38
	atk = 15
	range = 50
	mspd = 2.5
	aspd = 5.8
	level = 1
	def __init__(self, lanenum, isplayer):
		super().__init__(frames=Owl_duke.frames, hp=Owl_duke.hp, atk=Owl_duke.atk, range=Owl_duke.range, aspd=Owl_duke.aspd, mspd=Owl_duke.mspd, isplayer=isplayer, lanenum=lanenum)


class Item:
	def __init__(self, name, desc, cost):
		self.name = name
		self.desc = desc
		self.cost = cost
		self.isenabled = True

	def activate(self):
		pass

class CharItem(Item):
	def __init__(self, char, cost):
		super().__init__(char.__name__, char.desc, cost)
		self.char = char

	def activate(self):
		add(self.char, playerteam.units)
		self.isenabled = False

rockybg = PhotoImage(Image.open(r'pics\bg\rocky.bmp'))
beachbg = PhotoImage(Image.open(r'pics\bg\beach.bmp'))
forestbg = PhotoImage(Image.open(r'pics\bg\forest.bmp'))
desertbg = PhotoImage(Image.open(r'pics\bg\desert.bmp'))
cavebg = PhotoImage(Image.open(r'pics\bg\cave.bmp'))
gravebg = PhotoImage(Image.open(r'pics\bg\grave.bmp'))
menubutton = PhotoImage(Image.open(r'pics\menubutton.png'))
shadowpic = PhotoImage(Image.open(r'pics\shadow.png'))
battleuipic = PhotoImage(Image.open(r'pics\battleui.png'))
victorypic = PhotoImage(Image.open(r'pics\victoryscreen.png'))
defeatpic = PhotoImage(Image.open(r'pics\defeatscreen.png'))
menupic = PhotoImage(Image.open(r'pics\menu3.bmp'))
battlepic = PhotoImage(Image.open(r'pics\battlebg.bmp'))
fightbuttonpic = PhotoImage(Image.open(r'pics\fightbutton.png'))
slotbuttonpic = PhotoImage(Image.open(r'pics\slotbutton.png'))
selectedpic = PhotoImage(Image.open(r'pics\selected.png'))
shopbg = PhotoImage(Image.open(r'pics\shopbg.bmp'))
backarrowpic = PhotoImage(Image.open(r'pics\backarrow.png'))
uparrowpic = PhotoImage(Image.open(r'pics\uparrow.png'))
downarrowpic = PhotoImage(Image.open(r'pics\downarrow.png'))
borderpic = PhotoImage(Image.open(r'pics\border.png'))
upgradebg = PhotoImage(Image.open(r'pics\upgradebg.bmp'))
lanebuttonpic = PhotoImage(Image.open(r'pics\lanebutton.png'))
bookpic = PhotoImage(Image.open(r'pics\book.png'))
shoppage = 1
shopitems = {1 : [CharItem(Archer, 1000), CharItem(Assassin, 1500), CharItem(Knight, 2000), CharItem(Crusader, 2000), CharItem(Priest, 2500), CharItem(Prophet, 3000), CharItem(Taekwon, 3500), CharItem(Barbarian, 4000), CharItem(Minstrel, 4500), CharItem(Rifleman, 5000), CharItem(Champion, 5000)], 2: [], 3: []}
lanes = {1: [], 2: [], 3: []}
currentlevel = 1
mapmonsters = {rockybg: [AncientWorm, Angeling, Flora, Frilldora, Pecopeco, Petit, FlyingPetit, Poporing, Poring, Sidewinder, Skeggiold, Wormtail], beachbg: [Alligator, Ambernite, Anolian, Furseal, Merman, Mobster, Penomena, Phen, PirateSkeleton, Plankton, Shellfish], forestbg: [Nine_tail, Orc_archer, Orc_baby, Orc_lady, Ork_hero, Ork_warrior, Permeter, Pest, Spring_rabbit, Willow, Wolf, Wooden_golem, Wootan_shooter], desertbg: [Anacondaq, Ancient_mimic, Ancient_mummy, Condor, Desert_wolf, Dragon_fly, Kobold_archer, Zerom, Picky, Pharaoh, Pasana], cavebg: [Acidus_, Acidus, AmMut, Andre, AntEgg, Crystal, Freezer, Lava_Golem, Maya, Orc_zombie, Phreeoni, Piere, Pitman, Shelter, Zenorc, ZipperBear, Zombie_master, Zombie_prisoner, Zombie], gravebg: [Alarm, Alice, Alicel, Aliot, Antique_firelock, Frus, Ghostring, Hyegun, Miyabi_ningyo, Munak, Myst, Owl_baron, Owl_duke]}
bg = None
playerteam = Team(isplayer=True)
enemyteam = Team(isplayer=False)
teams = [playerteam, enemyteam]
purchases = []
add(Swordsman, playerteam.units)
slotsunits = {1: Swordsman, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None, 8: None}
unitpage = 1
numbooks = 0
money = 0

def saveandquit():
	if lexists(SAVENAME):
		file = open(SAVENAME, 'wb')
	else:
		file = open(SAVENAME, 'xb')
	saver = Pickler(file)
	saver.dump(numbooks)
	saver.dump(money)
	saver.dump(currentlevel)
	saver.dump(purchases)
	saver.dump(playerteam.units)
	chardict = {}
	for unit in playerteam.units:
		if 'basehp' not in unit.__dict__:
			unit.basehp = unit.hp
			unit.baseatk = unit.atk
		chardict[unit.__name__] = [unit.level, unit.basehp, unit.baseatk, unit.hp, unit.atk]
	saver.dump(chardict)
	monsterdict = {}
	for unit in [unit for lst in mapmonsters.values() for unit in lst]:
		if 'basehp' not in unit.__dict__:
			unit.basehp = unit.hp
			unit.baseatk = unit.atk
		monsterdict[unit.__name__] = [unit.level, unit.basehp, unit.baseatk, unit.hp, unit.atk]
	saver.dump(monsterdict)
	saver.dump(slotsunits)
	saver.dump(shopitems)

	file.close()

	window.destroy()


def load():
	global numbooks, money, currentlevel, purchases, slotsunits, shopitems

	if lexists(SAVENAME):
		file = open(SAVENAME, 'rb')
		loader = Unpickler(file)
		numbooks = loader.load()
		money = loader.load()
		currentlevel = loader.load()
		purchases = loader.load()
		playerteam.units = loader.load()
		unitdict = loader.load()
		for unitname in unitdict:
			globals()[unitname].level = unitdict[unitname][0]
			globals()[unitname].basehp = unitdict[unitname][1]
			globals()[unitname].baseatk = unitdict[unitname][2]
			globals()[unitname].hp = unitdict[unitname][3]
			globals()[unitname].atk = unitdict[unitname][4]
		monsterdict = loader.load()
		for unitname in monsterdict:
			globals()[unitname].level = monsterdict[unitname][0]
			globals()[unitname].basehp = monsterdict[unitname][1]
			globals()[unitname].baseatk = monsterdict[unitname][2]
			globals()[unitname].hp = monsterdict[unitname][3]
			globals()[unitname].atk = monsterdict[unitname][4]
		slotsunits = loader.load()
		shopitems = loader.load()

		file.close()

#load saved settings.
load()

def menu(event=None):
	canvas.delete(ALL)

	#draw background.
	canvas.create_image((0, 0), image=menupic, anchor='nw')

	#draw buttons shop, upgrade, battle, restart.
	tag = canvas.create_image((160, 120), image=menubutton)
	canvas.tag_bind(tag, '<ButtonPress-1>', shop)
	tag = canvas.create_image((480, 120), image=menubutton)
	canvas.tag_bind(tag, '<ButtonPress-1>', upgrade)
	tag = canvas.create_image((160, 410), image=menubutton)
	canvas.tag_bind(tag, '<ButtonPress-1>', battle)
	tag = canvas.create_image((480, 410), image=menubutton)
	canvas.tag_bind(tag, '<ButtonPress-1>', restart)

	#write current level.
	canvas.create_text((185, 420), text='Level: ' + str(currentlevel), font=REG_FONT)

def buy(item):
	global money
	if money >= item.cost and askyesno('Buy?', item.desc):
		item.activate()
		money -= item.cost
		shop()

def shop(event=None, page=1):
	global shoppage
	shoppage = page

	canvas.delete(ALL)

	#bg.
	canvas.create_image((0, 0), image=shopbg, anchor='nw')

	#back arrow.
	obj = canvas.create_image((70, 90), image=backarrowpic)
	canvas.tag_bind(obj, '<ButtonPress-1>', menu)

	#money.
	canvas.create_text((577, 44), text=money, anchor='e', font=BIG_FONT)

	#draw arrows.
	if shoppage > 1:
		obj = canvas.create_image((580, 230), image=uparrowpic)
		canvas.tag_bind(obj, '<ButtonPress-1>', lambda event: shop(event, shoppage - 1))
	if shoppage < len(shopitems):
		obj = canvas.create_image((580, 300), image=downarrowpic)
		canvas.tag_bind(obj, '<ButtonPress-1>', lambda event: shop(event, shoppage + 1))

	#draw shop items.
	x = 200
	y = 160
	for item in shopitems[shoppage]:
		obj = canvas.create_text((x, y), text=item.name, font=REG_FONT, anchor='w')
		canvas.tag_bind(obj, '<ButtonPress-1>', lambda event, i=item: buy(i))
		obj = canvas.create_text((460, y), text=str(item.cost) if item.isenabled else '--', font=REG_FONT, anchor='e')
		canvas.tag_bind(obj, '<ButtonPress-1>', lambda event, i=item: buy(i))
		canvas.create_image((130, y + 20), image=borderpic, anchor='w')
		y += 30

def up(unit):
	global numbooks
	if numbooks >= unit.level:
		if 'basehp' not in unit.__dict__:
			unit.basehp = unit.hp
			unit.baseatk = unit.atk

		newhp = unit.hp + unit.basehp * .2
		newatk = unit.atk + unit.baseatk * .2
		if askyesno('Upgrade ' + unit.__name__ + '?', 'HP: ' + str(int(unit.hp)) + ' -> ' + str(int(newhp)) + '\nATK: ' + str(int(unit.atk)) + ' -> ' + str(int(newatk))) is True:
			numbooks -= unit.level
			unit.level += 1
			unit.hp = newhp
			unit.atk = newatk
			upgrade()

def upgrade(event=None):
	canvas.delete(ALL)
	canvas.create_image((0, 0), image=upgradebg, anchor='nw')

	#back arrow.
	obj = canvas.create_image((72, 92), image=backarrowpic)
	canvas.tag_bind(obj, '<ButtonPress-1>', menu)

	#show num books.
	canvas.create_text((575, 55), text=numbooks, anchor='e', font=BIG_FONT)

	#draw units.
	x = 150
	y = 160
	for unit in playerteam.units:
		objs = [canvas.create_text((x, y), text=unit.__name__, font=REG_FONT, anchor='w'), canvas.create_text((430, y), text='Level: ' + str(unit.level), font=REG_FONT, anchor='e'), canvas.create_image((470, y), image=bookpic), canvas.create_text((490, y), text=unit.level, font=REG_FONT, anchor='w')]
		for obj in objs:
			canvas.tag_bind(obj, '<ButtonPress-1>', lambda event, u=unit: up(u))
		canvas.create_image((130, y + 20), image=borderpic, anchor='w') #draw border
		y += 30

def drag(event, obj):
	coords = canvas.coords(obj)
	canvas.move(obj, event.x - coords[0], event.y - coords[1])

def drop(event, obj, unit):
	coords = canvas.coords(obj)
	slotnum = None
	if coords[0] > 140 and coords[0] < 230 and coords[1] > 150 and coords[1] < 240 and not slotsunits[1]:
		slotnum = 1
		canvas.move(obj, 185 - coords[0], 195 - coords[1])
	elif coords[0] > 230 and coords[0] < 320 and coords[1] > 150 and coords[1] < 240 and not slotsunits[2]:
		slotnum = 2
		canvas.move(obj, 273 - coords[0], 195 - coords[1])
	elif coords[0] > 320 and coords[0] < 400 and coords[1] > 150 and coords[1] < 240 and not slotsunits[3]:
		slotnum = 3
		canvas.move(obj, 361 - coords[0], 195 - coords[1])
	elif coords[0] > 400 and coords[0] < 500 and coords[1] > 150 and coords[1] < 240 and not slotsunits[4]:
		slotnum = 4
		canvas.move(obj, 450 - coords[0], 195 - coords[1])

	elif coords[0] > 140 and coords[0] < 230 and coords[1] > 240 and coords[1] < 320 and not slotsunits[5]:
		slotnum = 5
		canvas.move(obj, 185 - coords[0], 280 - coords[1])
	elif coords[0] > 230 and coords[0] < 320 and coords[1] > 240 and coords[1] < 320 and not slotsunits[6]:
		slotnum = 6
		canvas.move(obj, 273 - coords[0], 280 - coords[1])
	elif coords[0] > 320 and coords[0] < 400 and coords[1] > 240 and coords[1] < 320 and not slotsunits[7]:
		slotnum = 7
		canvas.move(obj, 361 - coords[0], 280 - coords[1])
	elif coords[0] > 400 and coords[0] < 500 and coords[1] > 240 and coords[1] < 320 and not slotsunits[8]:
		slotnum = 8
		canvas.move(obj, 450 - coords[0], 280 - coords[1])
	else: #no slot? throw it in some random place in the pool.
		canvas.move(obj, randint(69, 470) - coords[0], randint(372, 433) - coords[1])

	for num in slotsunits:
		if slotsunits[num] is unit:
			slotsunits[num] = None
	if slotnum is not None:
		slotsunits[slotnum] = unit

def battle(event=None):
	global bg
	bg = [map for map in mapmonsters][(currentlevel - 1) % len(mapmonsters)]
	enemyteam.units = mapmonsters[bg]
	for team in teams:
		team.life = 100
		team.spawnpts = 0
		team.spawnrate = .15
		team.boostcost = 20

	canvas.delete(ALL)
	canvas.create_image((0, 0), image=battlepic, anchor='nw')

	#back arrow.
	obj = canvas.create_image((70, 90), image=backarrowpic)
	canvas.tag_bind(obj, '<ButtonPress-1>', menu)

	#draw unit slots.
	x = 0
	y = 0
	for unit in playerteam.units:
		if slotsunits[1] is unit:
			x = 185
			y = 195
		elif slotsunits[2] is unit:
			x = 273
			y = 195
		elif slotsunits[3] is unit:
			x = 361
			y = 195
		elif slotsunits[4] is unit:
			x = 450
			y = 195
		elif slotsunits[5] is unit:
			x = 185
			y = 280
		elif slotsunits[6] is unit:
			x = 273
			y = 280
		elif slotsunits[7] is unit:
			x = 360
			y = 280
		elif slotsunits[8] is unit:
			x = 450
			y = 280
		else:
			x = randint(69, 470)
			y = randint(372, 433)
		obj = canvas.create_image((x, y), image=unit.portrait)
		canvas.tag_bind(obj, '<B1-Motion>', lambda event, o=obj: drag(event, o))
		canvas.tag_bind(obj, '<ButtonRelease-1>', lambda event, o=obj, u=unit: drop(event, o, u))

	canvas.tag_bind(canvas.create_image((580, 450), image=fightbuttonpic), '<ButtonPress-1>', battleloop)


def restart(event=None):
	global currentlevel, purchases, numbooks, money
	if askyesno(title='Restart game?', message='Are you sure you want to reset all stats and level?') is True:
		for team in teams:
			for unit in team.units:
				if unit.level > 1:
					unit.level = 1
					unit.hp = unit.basehp
					unit.atk = unit.baseatk
		for slot in slotsunits:
			slotsunits[slot] = None
		purchases = []
		currentlevel = 1
		money = 0
		numbooks = 0
		menu()

def showvictory(event=None):
	global currentlevel, money, numbooks
	for monster in mapmonsters[bg]:
		if 'basehp' not in monster.__dict__:
			monster.basehp = monster.hp
			monster.baseatk = monster.atk
		monster.hp += monster.basehp * .5
		monster.atk += monster.baseatk * .5
	currentlevel += 1
	money += 500
	numbooks += 1
	canvas.tag_bind(canvas.create_image((0, 0), image=victorypic, anchor='nw'), '<ButtonPress-1>', menu)

def showdefeat(event=None):
	canvas.tag_bind(canvas.create_image((0, 0), image=defeatpic, anchor='nw'), '<ButtonPress-1>', menu)

def battleloop(event=None):
	canvas.delete(ALL)
	canvas.create_image((0, 0), image=bg, anchor='nw')

	#check if winner.
	if playerteam.life <= 0:
		winner = enemyteam
	elif enemyteam.life <= 0:
		winner = playerteam
	else:
		winner = None

	#no winner? keep drawing units.
	if winner is None:
		for num in range(1, 4):
			for obj in lanes[num]:
				obj.run()
	else:
		if winner is playerteam:
			showvictory()
		else:
			showdefeat()
		for lane in lanes.values():
			clear(lane)
		return

	#update teams' spawn points.
	for team in teams:
		team.spawnpts += team.spawnrate

		#spawn enemies at random.
		if team is enemyteam:
			if team.spawnpts >= team.boostcost:
				team.boost()
			team.unit = team.units[randint(0, len(team.units) - 1)]
			lanenum = randint(1, 3)
			if randint(0, 20) > 19:
				team.deploy(lanenum)

	#make interface.
	canvas.create_rectangle((282, 40, 282 - playerteam.life * 2, 55), outline='', fill='#0093d8') #player life
	canvas.create_rectangle((350, 40, 350 + enemyteam.life * 2, 55), outline='', fill='#ee1846') #enemy life
	canvas.create_image((0, 0), image=battleuipic, anchor='nw')
	canvas.create_text((590, 25), text=money, anchor='e', font=BIG_FONT) #money
	canvas.create_text((60, 400), text=str(int(playerteam.spawnpts)), font=BIG_FONT) #boost info
	canvas.create_text((86, 450), text=str(int(playerteam.boostcost)), font=REG_FONT, anchor='w')
	obj = canvas.create_image((60, 400), image=slotbuttonpic)
	canvas.tag_bind(obj, '<ButtonPress-1>', lambda event: playerteam.boost()) #deploy buttons
	obj = canvas.create_image((10, 143), image=lanebuttonpic, anchor='nw')
	canvas.tag_bind(obj, '<ButtonPress-1>', lambda event: playerteam.deploy(1))
	obj = canvas.create_image((10, 209), image=lanebuttonpic, anchor='nw')
	canvas.tag_bind(obj, '<ButtonPress-1>', lambda event: playerteam.deploy(2))
	obj = canvas.create_image((10, 280), image=lanebuttonpic, anchor='nw')
	canvas.tag_bind(obj, '<ButtonPress-1>', lambda event: playerteam.deploy(3))

	drawslots(unitpage)
	if unitpage is 1:
		obj = canvas.create_image((600, 400), image=uparrowpic)
		canvas.tag_bind(obj, '<ButtonPress-1>', lambda event: drawslots(unitpage + 1))
	else:
		obj = canvas.create_image((600, 400), image=downarrowpic)
		canvas.tag_bind(obj, '<ButtonPress-1>', lambda event: drawslots(unitpage - 1))

	#recurse.
	canvas.after(TICKTIME, battleloop)

def drawslots(num):
	global unitpage
	unitpage = num

	x = -100
	y = -100
	if (unitpage is 1 and slotsunits[1] and slotsunits[1] is playerteam.unit) or (unitpage is 2 and slotsunits[5] and slotsunits[5] is playerteam.unit):
		x = 126
		y = 439
	elif (unitpage is 1 and slotsunits[2] and slotsunits[2] is playerteam.unit) or (unitpage is 2 and slotsunits[6] and slotsunits[6] is playerteam.unit):
		x = 236
		y = 439
	elif (unitpage is 1 and slotsunits[3] and slotsunits[3] is playerteam.unit) or (unitpage is 2 and slotsunits[7] and slotsunits[7] is playerteam.unit):
		x = 347
		y = 439
	elif (unitpage is 1 and slotsunits[4] and slotsunits[4] is playerteam.unit) or (unitpage is 2 and slotsunits[8] and slotsunits[8] is playerteam.unit):
		x = 457
		y = 439
	canvas.create_image((x, y), anchor='sw', image=selectedpic) #highlight chosen slot
	x = 175
	y = 400
	if unitpage == 1:
		ranges = range(1, 5)
	else:
		ranges = range(5, 9)

	#draw unit slots.
	for num in ranges:
		if slotsunits[num] is None:
			x += 114
			continue
		obj = canvas.create_image((x, y), image=slotsunits[num].portrait) #draw head
		canvas.tag_bind(obj, '<ButtonPress-1>', lambda event, u=slotsunits[num]: chooseunit(u))
		canvas.create_text((x, y + 50), text=slotsunits[num].cost, font=REG_FONT, fill='white') #write cost
		x += 114


def chooseunit(unitclass):
	playerteam.unit = unitclass

window.bind_all('<KeyRelease-1>', lambda event: playerteam.deploy(1))
window.bind_all('<KeyRelease-2>', lambda event: playerteam.deploy(2))
window.bind_all('<KeyRelease-3>', lambda event: playerteam.deploy(3))
window.protocol("WM_DELETE_WINDOW", saveandquit)

window.after(0, menu)
window.mainloop()