import bt
import time
import math
import sys
import random
from termcolor import colored

class WalkAction(bt._BaseNode):

    def __init__(self, dest):
        self.dest = dest

    def tick(self, ctx):
        agent = ctx.target
        if agent.pos == self.dest:
            return bt.OK
        agent.begin_walkToward(self.dest)
        return bt.RUNNING


class WalkAwayFromEnemy(bt._BaseNode):

    def tick(self, ctx):
        agent = ctx.target
        agent.begin_retreating()
        return bt.RUNNING


class AttackEnemy(bt._BaseNode):

    def tick(self, ctx):
        agent = ctx.target
        targets = agent.nearbyThings(agent.attack_range)
        if not targets:
            return bt.FAIL
        else:
            if agent.begin_attacking(targets[0]):
                return bt.RUNNING
            else:
                return bt.FAIL

class Rest(bt._BaseNode):

    def tick(self, ctx):
        ctx.target.begin_resting()


class IsEnemyNear(bt._BaseNode):

    def tick(self, ctx):
        agent = ctx.target
        things = agent.nearbyThings(agent.attack_range)
        if things:
            return bt.OK
        else:
            return bt.FAIL


class IsHealthyCheck(bt._BaseNode):

    def tick(self, ctx):
        if ctx.target.health >= 50:
            return bt.OK
        else:
            return bt.FAIL





class Thing(object):

    pos = 0


class Agent(object):

    char = 'x'
    pos = 0,0
    walking_speed = 2.0
    health = 100
    dead = False

    attack_range = 3
    attack_rate = 1.0
    attack_damage = (1, 4)

    rest_rate = 0.5
    restore_amount = (2, 4)

    target_pos = None

    def __init__(self, world):
        self.states = set()
        self.world = world

    def tick(self, context):
        for state in list(self.states):
            m = getattr(self, 'tick_{0}'.format(state), lambda x:None)
            m(context)

    def nearbyThings(self, max_distance):
        near = []
        for thing in self.world['things']:
            if thing == self:
                continue
            d = self.distanceTo(thing.pos)
            if d <= max_distance:
                near.append((d, thing))
        near = sorted(near, key=lambda x:x[0])
        return [x[1] for x in near]

    def distanceTo(self, pos):
        dir_x = float(pos[0]) - self.pos[0]
        dir_y = float(pos[1]) - self.pos[1]
        return (dir_x**2 + dir_y**2)**0.5

    def begin_attacking(self, what):
        # XXX the math is probably wrong
        if self.distanceTo(what.pos) <= self.attack_range:
            self.states.add('attacking')
            self.punching_target = what
            self.begin_walkToward(what.pos)
            return True
        if 'attacking' in self.states:
            self.states.remove('attacking')
        return False

    def tick_attacking(self, context):
        if self.distanceTo(self.punching_target.pos) > self.attack_range:
            self.states.remove('attacking')
            return
        attack_timer = getattr(self, 'attack_timer', 0)
        attack_timer -= context.time_delta
        if attack_timer < 0:
            self.punching_target.bedamaged(random.randint(*self.attack_damage))
            self.attack_timer = self.attack_rate + attack_timer
        else:
            self.attack_timer = attack_timer

    def begin_resting(self):
        # XXX the math is probably wrong
        self.states.add('resting')

    def tick_resting(self, context):
        if len(self.states) > 1:
            self.states.remove('resting')
            return
        rest_timer = getattr(self, 'rest_timer', 0)
        rest_timer -= context.time_delta
        if rest_timer < 0:
            self.restorehealth(random.randint(*self.restore_amount))
            self.rest_timer = self.rest_rate + rest_timer
        else:
            self.rest_timer = rest_timer

    def begin_retreating(self):
        self.states.add('retreating')

    def tick_retreating(self, context):
        nearby = self.nearbyThings(self.attack_range + 2)
        if nearby:
            nearest = nearby[0]
            v = self.unitVector(nearest.pos, self.pos) * self.attack_range 
            if v == (0,0):
                v = (math.randint(0,1), math.randint(0, 1))
            target = self.pos[0] + v[0], self.pos[1] + v[1]
            self.begin_walkToward(target)
        else:
            self.states.remove('retreating')


    def begin_walkToward(self, pos):
        self.target_pos = pos
        self.states.add('walking')

    def tick_walking(self, context):
        # XXX no obstacles handled and the math is probably wrong
        v = self.unitVector(self.pos, self.target_pos)
        distance_walked = context.time_delta * self.walking_speed
        distance_left = self.distanceTo(self.target_pos)
        distance_walked = min([distance_walked, distance_left])
        amt_x = math.copysign(min([abs(v[0]), abs(v[0]) * distance_walked]), v[0])
        amt_y = math.copysign(min([abs(v[1]), abs(v[1]) * distance_walked]), v[1])
        self.pos = amt_x + self.pos[0], amt_y + self.pos[1]
        if self.pos == self.target_pos:
            self.states.remove('walking')

    def unitVector(self, a, b):
        dir_x = float(b[0]) - a[0]
        dir_y = float(b[1]) - a[1]
        total = abs(dir_x) + abs(dir_y)
        try:
            amt_x = math.copysign(abs(dir_x) / total, dir_x)
        except ZeroDivisionError:
            amt_x = 0
        try:
            amt_y = math.copysign(abs(dir_y) / total, dir_y)
        except ZeroDivisionError:
            amt_y = 0
        return amt_x, amt_y


    def bedamaged(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.dead = True

    def restorehealth(self, amount):
        self.health += amount
        if self.health > 100:
            self.health = 100




class EngineContext(object):

    def __init__(self, time_delta):
        self.time_delta = time_delta


def displayBoard(agents, h=10, w=10):
    mapping = {}
    for a in agents:
        color = 'green'
        if a.health <= 0:
            color = 'red'
        elif a.health <= 50:
            color = 'yellow'
        elif a.health <= 75:
            color = 'white'
        char = colored(a.char, color)
        mapping[(int(a.pos[0]), int(a.pos[1]))] = char
        print '{char}: {a.health} {states}'.format(char=char, a=a, states=list(a.states))

    for r in xrange(h):
        if r == 0:
            sys.stdout.write('0' * (w+1) + '\n')
        for c in xrange(w):
            if c == 0 or c == w-1:
                sys.stdout.write('0')
            char = mapping.get((r,c), ' ')
            sys.stdout.write(char)
        sys.stdout.write('\n')
        if r == h-1:
            sys.stdout.write('0' * (w+1) + '\n')


if __name__ == '__main__':
    tree = bt.BehaviorTree(
        bt.Priority('behave', [
            bt.Sequence('handle enemy', [
                IsEnemyNear(),
                bt.Priority('fight or flight', [
                    bt.Sequence('flight', [
                        bt.Inverter(IsHealthyCheck()),
                        WalkAwayFromEnemy(),
                    ]),
                    bt.Sequence('fight', [
                        IsHealthyCheck(),
                        AttackEnemy(),
                    ])
                ]) 
            ]),
            bt.Sequence('be healthy', [
                bt.Inverter(IsHealthyCheck()),
                Rest(),
            ]),
            bt.Sequence('walk around', [
                bt.WaitAction(1),
                bt.MemSequence('walk around', [
                    WalkAction((2,0)),
                    WalkAction((2,2)),
                    WalkAction((0,2)),
                    WalkAction((2,4)),
                ]),
            ]),
        ])
    )
    world = {'things': []}
    agent1 = Agent(world)
    agent2 = Agent(world)
    agent2.pos = 8, 4
    agent2.char = 'T'
    agent2.attack_damage = (3, 5)

    world['things'].extend([agent1, agent2])

    blackboard1 = bt.Blackboard()
    blackboard2 = bt.Blackboard()
    last_time = time.time()
    while True:
        tree.tick(agent1, blackboard1)
        tree.tick(agent2, blackboard2)
        now = time.time()
        ctx = EngineContext(now - last_time)
        agent1.tick(ctx)
        agent2.tick(ctx)
        last_time = now
        displayBoard([agent1, agent2])
        time.sleep(0.05)
