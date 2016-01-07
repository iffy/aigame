import bt
import time
import math
import sys


class WalkAction(bt._BaseNode):

    def __init__(self, dest):
        self.dest = dest

    def tick(self, ctx):
        agent = ctx.target
        if agent.pos == self.dest:
            return bt.OK
        agent.begin_walkToward(self.dest)
        return bt.RUNNING



class Thing(object):

    pos = 0


class Agent(object):

    char = 'x'
    pos = 0,0
    walking_speed = 2.0

    target_pos = None

    def __init__(self):
        self.states = set()

    def begin_walkToward(self, pos):
        self.target_pos = pos
        self.states.add('walking')

    def tick(self, context):
        for state in list(self.states):
            m = getattr(self, 'tick_{0}'.format(state), lambda x:None)
            m(context)

    def tick_walking(self, context):
        # XXX no obstacles handled
        dir_x = float(self.target_pos[0]) - self.pos[0]
        dir_y = float(self.target_pos[1]) - self.pos[1]
        total = abs(dir_x) + abs(dir_y)
        distance_walked = context.time_delta * self.walking_speed
        amt_x = math.copysign(min([abs(dir_x), abs(dir_x) / total * distance_walked]), dir_x)
        amt_y = math.copysign(min([abs(dir_y), abs(dir_y) / total * distance_walked]), dir_y)
        self.pos = amt_x + self.pos[0], amt_y + self.pos[1]
        if self.pos == self.target_pos:
            self.states.remove('walking')




class EngineContext(object):

    def __init__(self, time_delta):
        self.time_delta = time_delta


def displayBoard(agents, h=10, w=10):
    mapping = {}
    for a in agents:
        mapping[(int(a.pos[0]), int(a.pos[1]))] = a.char

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
    tree = bt.BehaviorTree(bt.Sequence('look busy', [
        bt.WaitAction(1),
        bt.MemSequence('walk around', [
            WalkAction((2,0)),
            WalkAction((2,2)),
            WalkAction((0,2)),
            WalkAction((2,4)),
        ]),
    ]))
    agent1 = Agent()
    agent2 = Agent()
    agent2.pos = 8, 4
    agent2.char = 'T'
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
