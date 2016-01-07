import yaml
import time
from twisted.internet import defer, task, reactor

NORESULT = object()


class Selector(object):
    """
    I succeed on the first success of children and only fail
    if all my children fail.
    """

    def __init__(self, name=None, children=None):
        self.name = name
        self.children = children or []

    def run(self, world, actor):
        for c in self.children:
            ret = c.run(world, actor)
            if ret != False:
                return ret
        return False

    def reset(self):
        for c in self.children:
            c.reset()


class Sequence(object):
    """
    I fail on the first failure of my children and only succeed
    if all my children succeed.
    """

    def __init__(self, name=None, children=None):
        self.name = name
        self.children = children or []

    def run(self, world, actor):
        for c in self.children:
            ret = c.run(world, actor)
            if ret != True:
                return ret
        return True

    def reset(self):
        for c in self.children:
            c.reset()


class Action(object):
    """
    I run a function.  It should return one of
    True (succeed), False (failure), None (running)
    """

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._current = NORESULT

    def run(self, world, actor):
        if self._current != NORESULT:
            # already have a result
            return self._current
        try:
            ret = self.func(world, actor, *self.args, **self.kwargs)
        except:
            return False
        if ret == True:
            return True
        elif isinstance(ret, defer.Deferred):
            self._current = None
            ret.addCallback(self._gotResult)
            ret.addErrback(self._gotError)
            return None
        else:
            return False

    def reset(self):
        self._current = NORESULT

    def _gotResult(self, result):
        self._current = result

    def _gotError(self, err):
        self._current = False



def distanceBetween(a, b):
    ret = abs(b - a)
    return ret

def thingsNear(subject, distance):
    """
    Return a list of things within a certain distance of the subject.
    """
    for thing in subject['$world']['things'].values():
        try:
            if distanceBetween(subject['pos'], thing['pos']) <= distance:
                yield thing['id']
        except (KeyError, TypeError):
            pass

def thingsInSight(subject):
    """
    Generate a list of things in sight of the subject.
    """
    return thingsNear(subject, subject.get('see_distance', 0))

def reachableThings(subject):
    """
    Generate a list of that the subject can currently reach
    without moving.
    """
    return thingsNear(subject, subject.get('reach_distance', 0))


def walkTo(world, actor, pos):
    # start walking
    d = defer.Deferred()
    distance = distanceBetween(actor['pos'], pos)
    time = distance / actor.get('walking_speed', 1)
    def stop(actor, pos):
        actor['pos'] = pos
        d.callback(True)
    reactor.callLater(time, stop, actor, pos)
    return d


def MoveToPositionTree(goal_position):
    return Selector('moveTo{0}'.format(goal_position), [
        Action(walkTo, goal_position),
    ])


world = {
    'things': {},
    'time': 0,
}


def addThing(id, data):
    data['id'] = id
    data['$world'] = world
    world['things'][id] = data
    return data

if __name__ == '__main__':
    sam = addThing('sam', {
        'pos': 0,
        'see_distance': 1,
        'reach_distance': 0,
    })
    addThing('apple', {
        'pos': 0,
        'types': ['edible', 'fruit'],
    })
    addThing('banana', {
        'pos': 0,
        'types': ['edible', 'fruit'],
    })
    addThing('carrot', {
        'pos': 1,
        'types': ['edible', 'vegetable'],
    })

    print 'can see  ', list(thingsInSight(sam))
    print 'can reach', list(reachableThings(sam))

    tree = MoveToPositionTree(1)

    def tick():
        world['time'] = time.time()
        print 'tree.run', tree.run(world, sam)
        #print yaml.safe_dump(world)
        print 'pos', sam['pos']

    lc = task.LoopingCall(tick)
    lc.start(0.1)
    reactor.run()

    



