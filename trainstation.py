import copy
import json
from collections import defaultdict


def ofType(thing, thing_type):
    """
    Return C{True} if this thing is of the given type.
    """
    return thing_type in thing.get('types', [])

def hasThing(actor, thing):
    """
    Return C{True} if the C{actor} has C{thing}.
    """
    return thing in actor.get('inventory', [])

def hasThingOfType(actor, thing_type):
    """
    Return C{True} if the actor has a thing of the given type in their inventory.
    """
    for item in actor.get('inventory', []):
        if ofType(item, thing_type):
            return True
    return False


class Arg(object):

    def __init__(self, name, type=None, had_by=None):
        self.name = name
        self.type = type
        self.had_by = had_by

    def matchesThing(self, thing, current_args=None):
        """
        Return C{True} if the given thing matches this requirements of this
        argument.
        """
        current_args = current_args or {}
        conds = []
        if self.type is not None:
            conds.append(ofType(thing, self.type))
        if self.had_by is not None:
            conds.append(hasThing(current_args[self.had_by], thing))
        return all(conds)


class Action(object):

    args = []

    def timeEstimate(self, args, world):
        """
        Return perceived numeric time required to do this action.
        """
        raise NotImplemented
    
    # timeEstimate = 0
    # moneycost = 0
    # # riskiness?
    # # unpleasantness?

    def preconditionsMet(self, args, world):
        """
        Return C{True} if the prerequisites for this action are met, otherwise
        C{False}
        """
        raise NotImplemented

    def effectEffects(self, args, world):
        """
        Return a new L{Context} with the effects of this action done.
        """
        raise NotImplemented


class Walk(Action):

    args = [
        Arg('actor', type='biped'),
        Arg('dest', type='location'),
    ]

    def timeEstimate(self, (actor, dest), world):
        distance = abs(location['coordinates'] - actor['coordinates'])
        return actor['walking_speed'] * distance
    
    def preconditionsMet(self, (actor, dest), world):
        return actor['coordinates'] != dest['coordinates']

    def effectEffects(self, (actor, dest), world):
        actor['coordinates'] = dest['coordinates']


class Ride(Action):

    args = [
        Arg('actor', type='biped'),
        Arg('rideable', type='rideable', had_by='actor'),
        Arg('dest', type='location'),
    ]

    def timeEstimate(self, (actor, rideable, dest), world):
        distance = abs(dest['coordinates'] - actor['coordinates'])
        return rideable['speed'] * distance
    
    def preconditionsMet(self, (actor, rideable, dest), world):
        return actor['coordinates'] != dest['coordinates']

    def effectEffects(self, (actor, rideable, dest), world):
        actor['coordinates'] = dest['coordinates']


class Node(object):

    def __init__(self, data):
        self.data = data
        self.children = []

    def addChild(self, edge_data, child):
        self.children.append((edge_data, child))


class Path(object):

    def __init__(self, src, dst, data):
        self.src = src
        self.dst = dst
        self.data = data


class Planner(object):

    def __init__(self):
        self.all_actions = []

    def possiblePathsToGoal(self, actor_name, world, goal_func, args=None, kwargs=None):
        """
        Return all possible paths to a particular goal state.

        @param goal_func: A function that should return True if the goal is achieved,
            and False if it is not achieved.  Called like this:
            goal_func(future_actor, future_world, *args, **kwargs)
        """
        args = args or ()
        kwargs = kwargs or {}
        all_worlds, edges = self.buildActionTree(actor_name, world)
        succeeded = []
        print 'worlds', len(all_worlds)
        for world in all_worlds:
            actor = world['things'][actor_name]
            if goal_func(actor, world, *args, **kwargs):
                print 'success state found!', world
                succeeded.append(world)

        # walk the tree
        # XXX super ineefificnet.  It's 11pm

        return []


    def buildActionTree(self, actor_name, world):
        """

        """
        starting_node = copy.deepcopy(world)
        work = [starting_node]
        all_worlds = []
        edges = []
        while work:
            old_world = work.pop(0)
            if old_world in all_worlds:
                # old_world already all_worlds
                continue
            all_worlds.append(old_world)
            #print 'processing old_world', old_world.data

            actor = old_world['things'][actor_name]
            for action, args in self.possibleNextActions(actor, old_world):
                new_world = copy.deepcopy(old_world)
                real_args = [new_world['things'][x['name']] for x in args]
                action.effectEffects(real_args, new_world)
                work.append(new_world)

                # process new world
                edge = Path(old_world, new_world, (action, real_args))
                edges.append(edge)
            print 'len work', len(work)

        return all_worlds, edges


    def prepArgs(self, action, kwargs):
        return [kwargs[arg.name] for arg in action.args]

    def possibleNextActions(self, actor, world):
        """
        Returns a list of all the possible actions this actor can perform
        """
        candidates = world['things'].values()
        for action, kwargs in self._possibleActionsByArgRequirements(actor, candidates):
            args = self.prepArgs(action, kwargs)
            if not action.preconditionsMet(args, world):
                continue
            yield action, args

    def _possibleActionsByArgRequirements(self, actor, candidates):
        result = []
        # find all the actions that this actor can do.
        doable = (x for x in self.all_actions if x.args[0].matchesThing(actor))

        for action in doable:
            current_args = {action.args[0].name: actor}

            # find suitable options for other arguments
            if action.args[1:]:
                for x in self.candidateArgs(current_args, action.args[1:], candidates):
                    yield action, x
            else:
                yield action, current_args

    def findArgCandidates(self, current_args, arg, candidates):
        """
        Generate a list of the potential candidates for a single argument.
        """
        for candidate in candidates:
            if arg.matchesThing(candidate, current_args):
                yield candidate

    def candidateArgs(self, current_args, arglist, candidates):
        """
        Generate a list of potential arg calls.
        """
        arg = arglist[0]
        valids = self.findArgCandidates(current_args, arg, candidates)
        for valid in valids:
            new_args = {}
            for k, v in current_args.items():
                new_args[k] = v
            new_args[arg.name] = valid
            if arglist[1:]:
                # there are more args
                for x in self.candidateArgs(new_args, arglist[1:], candidates):
                    yield x
            else:
                yield new_args


def runSimulation():
    planner = Planner()
    planner.all_actions.append(Walk())
    planner.all_actions.append(Ride())

    world = {
        'things': {},
    }

    def addThing(name, x):
        x['name'] = name
        world['things'][name] = x
        return x

    bob = addThing('bob', {
        'types': ['biped'],
        'walking_speed': 1,
        'coordinates': 0,
    })
    home = addThing('home', {
        'types': ['location'],
        'coordinates': 0,
    })
    work = addThing('work', {
        'types': ['location'],
        'coordinates': 5,
    })
    gym = addThing('gym', {
        'types': ['location'],
        'coordinates': -1,
    })
    bike = addThing('red bike', {
        'types': ['rideable'],
        'speed': 2,
        'coordinates': 0,
    })

    # for x in planner.possibleNextActions(bob, world):
    #     print x

    def goal(actor, world):
        return actor['coordinates'] == world['things']['work']['coordinates']

    for x in planner.possiblePathsToGoal('bob', world, goal):
        print x




if __name__ == '__main__':
    runSimulation()
