import copy


def ofType(thing, thing_type):
    """
    Return C{True} if this thing is of the given type.
    """
    return thing_type in thing.get('types', [])

def hasThing(actor, thing):
    """
    Return C{True} if the C{actor} has C{thing}.
    """
    return thing['id'] in actor.get('inventory', [])

def hasThingOfType(actor, thing_type):
    """
    Return C{True} if the actor has a thing of the given type in their inventory.
    """
    for item in actor.get('inventory', []):
        if ofType(item, thing_type):
            return True
    return False

def distanceBetween(a, b):
    return abs(b['coordinates'] - a['coordinates'])


class Arg(object):

    def __init__(self, name, type=None, has_attr=None, had_by=None):
        self.name = name
        self.type = type
        self.has_attr = has_attr or []
        if not isinstance(self.has_attr, list):
            self.has_attr = [self.has_attr]
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
        for attr in self.has_attr:
            conds.append(attr in thing)
        if self.had_by is not None:
            conds.append(hasThing(current_args[self.had_by], thing))
        return all(conds)




def computeCost(actor, time=0, money=0, disgust=0, badness=0):
    """
    @param time: seconds
    @param money: dollars
    @param disgust: disgust units :)
    @param badness: moral badness of an action, in badness units.
    """
    # standard weights -- everything is relative to an hour of time
    time_weight = 1/3600.0
    money_weight = actor.get('money_value', 20)
    disgust_weight = 20
    badness_weight = actor.get('morality', 1) * 20

    return sum([
        (time_weight * time),
        (money_weight * money),
        (disgust_weight * disgust),
        (badness_weight * badness),
    ])


class Action(object):

    name = None
    args = []

    def getName(self):
        return self.name or (self.__class__.__name__)

    def bind(self, arg_ids):
        if isinstance(arg_ids, dict):
            arg_ids = [arg_ids[arg.name]['id'] for arg in self.args]
        return BoundAction(self, arg_ids)

    def timecost(self, args, world):
        """
        Return the number of seconds the action takes.
        """
        return 0

    def cost(self, args, world):
        """
        Return a numeric cost associated with this action.
        """
        return self.timecost(args, world)

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

    def __repr__(self):
        return '<Action:{0}>'.format(self.getName())


class BoundAction(object):

    def __init__(self, action, arg_ids):
        self.action = action
        self.args = arg_ids

    def _callMethod(self, name, world):
        real_args = [world['things'][x] for x in self.args]
        return getattr(self.action, name)(real_args, world)

    def cost(self, world):
        return self._callMethod('cost', world)

    def preconditionsMet(self, world):
        return self._callMethod('preconditionsMet', world)

    def effectEffects(self, world):
        return self._callMethod('effectEffects', world)

    def __repr__(self):
        return '<BoundAction {0!r} {1!r}>'.format(self.action, self.args)

    def __str__(self):
        return '{0}{1!r}'.format(self.action.getName(), self.args)


class Node(object):

    def __init__(self, data):
        self.data = data
        self.children = []

    def addChild(self, edge_data, child):
        self.children.append((edge_data, child))

    def __repr__(self):
        return '<Node {0!r} {1}>'.format(self.data, len(self.children))

    def walk(self):
        """
        Generate each child, without edge information.
        """
        yield self
        for (edge,child) in self.children:
            for x in child.walk():
                yield x

    def listPaths(self):
        """
        Generate a (path, node) for each path/node pair.
        """
        yield [], self
        for (edge, child) in self.children:
            for path, node in child.listPaths():
                yield [edge] + path, node


class Path(object):

    def __init__(self, src, dst, data):
        self.src = src
        self.dst = dst
        self.data = data


class Goal(object):

    def __init__(self, check, whittle=None):
        self.check = check
        if whittle:
            self.whittle = whittle

    def whittle(self, world):
        return copy.deepcopy(world['things'])


class Planner(object):

    def __init__(self):
        self.all_actions = []

    def bestPathsToGoal(self, actor_id, world, goal):
        """
        Return best paths to a particular goal state.

        @param goal: An instance of L{Goal}.
        """
        # XXX not an efficient algorithm
        paths_with_cost = []

        for path in self.possiblePathsToGoal(actor_id, world, goal):
            total_cost = 0
            action_world = copy.deepcopy(world)
            for action in path:
                total_cost += action.cost(action_world)
                action.effectEffects(action_world)
            paths_with_cost.append((path, total_cost))

        best_cost = min(x[1] for x in paths_with_cost)

        for path, cost in paths_with_cost:
            if cost == best_cost:
                yield path

    def possiblePathsToGoal(self, actor_id, world, goal):
        """
        Return all possible paths to a particular goal state.

        @param goal: An instance of L{Goal}.
        """
        tree = self.buildActionTree(actor_id, world, goal)

        # find end states
        goal_nodes = []
        for x in tree.walk():
            if goal.check(x.data):
                goal_nodes.append(x)
        
        for path, node in tree.listPaths():
            if node in goal_nodes:
                yield path

    def buildActionTree(self, actor_id, world, goal):
        """

        """
        starting_world = copy.deepcopy(world)
        done = []
        tree = Node(starting_world)
        work = [tree]
        while work:
            old_node = work.pop(0)
            whittled = goal.whittle(old_node.data)
            if whittled in done:
                # old_node already done
                continue
            done.append(whittled)

            old_world = old_node.data
            for action in self.possibleNextActions(actor_id, old_world):
                new_world = copy.deepcopy(old_world)
                action.effectEffects(new_world)

                # fill out tree
                new_node = Node(new_world)
                old_node.addChild(action, new_node)
                
                # add new world to queue
                work.append(new_node)
        return tree


    def prepArgs(self, action, kwargs):
        return [kwargs[arg.name] for arg in action.args]

    def possibleNextActions(self, actor_id, world):
        """
        Returns a list of all the possible actions this actor can perform
        """
        candidates = world['things'].values()
        actor = world['things'][actor_id]
        for bound_action in self._possibleActionsByArgRequirements(actor, candidates):
            if not bound_action.preconditionsMet(world):
                continue
            yield bound_action

    def _possibleActionsByArgRequirements(self, actor, candidates):
        # find all the actions that this actor can do.
        doable = (x for x in self.all_actions if x.args[0].matchesThing(actor))

        for action in doable:
            current_args = {action.args[0].name: actor}

            # find suitable options for other arguments
            if action.args[1:]:
                for x in self.candidateArgs(current_args, action.args[1:], candidates):
                    yield action.bind(x)
            else:
                yield action.bind(current_args)

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


class Walk(Action):

    args = [
        Arg('actor', has_attr='walking_speed'),
        Arg('dest', type='location'),
    ]

    def cost(self, (actor, dest), world):
        distance = distanceBetween(actor, dest)
        time_cost = distance / actor['walking_speed']
        return computeCost(actor, time=time_cost)
    
    def preconditionsMet(self, (actor, dest), world):
        return actor['coordinates'] != dest['coordinates']

    def effectEffects(self, (actor, dest), world):
        actor['coordinates'] = dest['coordinates']


class Ride(Action):

    args = [
        Arg('actor', type='biped'),
        Arg('rideable', type='rideable', has_attr='speed', had_by='actor'),
        Arg('dest', type='location'),
    ]

    def cost(self, (actor, rideable, dest), world):
        distance = distanceBetween(actor, dest)
        time_cost = distance / rideable['speed']
        return computeCost(actor, time=time_cost)
    
    def preconditionsMet(self, (actor, rideable, dest), world):
        return actor['coordinates'] != dest['coordinates']

    def effectEffects(self, (actor, rideable, dest), world):
        actor['coordinates'] = dest['coordinates']


class Take(Action):

    args = [
        Arg('actor', has_attr='inventory'),
        Arg('obj', type='takeable'),
    ]

    def cost(self, (actor, obj), world):
        # It's bad to steal
        badness = obj.get('price', 0) * 100
        return computeCost(actor, time=0.01, badness=badness)

    def preconditionsMet(self, (actor, obj), world):
        try:
            if actor['coordinates'] != obj['coordinates']:
                return False
        except KeyError:
            return False
        return True

    def effectEffects(self, (actor, obj), world):
        actor['inventory'].append(obj['id'])
        obj.pop('coordinates')


class Drop(Action):

    args = [
        Arg('actor', has_attr='inventory'),
        Arg('obj', had_by='actor'),
    ]

    def preconditionsMet(self, (actor, obj), world):
        # XXX conditions defined by args are sufficient
        return True

    def effectEffects(self, (actor, obj), world):
        obj['coordinates'] = actor['coordinates']
        actor['inventory'].remove(obj['id'])


class Buy(Action):

    args = [
        Arg('actor', has_attr=['inventory', 'money']),
        Arg('obj', type='takeable', has_attr='price'),
    ]

    def cost(self, (actor, obj), world):
        return computeCost(actor, time=0.01, money=obj['price'])

    def preconditionsMet(self, (actor, obj), world):
        try:
            if actor['coordinates'] != obj['coordinates']:
                return False
        except KeyError:
            return False
        return actor['money'] >= obj['price']

    def effectEffects(self, (actor, obj), world):
        actor['money'] -= obj['price']
        actor['inventory'].append(obj['id'])
        obj.pop('coordinates')
        obj['value'] = obj.pop('price')


class Use(Action):

    args = [
        Arg('actor'),
        Arg('obj', type='useable'),
    ]

    def cost(self, (actor, obj), world):
        time_cost = 0
        if 'coordinates' in obj['effect'] and 'speed' in obj['effect']:
            distance = distanceBetween(actor, obj['effect'])
            time_cost = distance / obj['effect']['speed']
        return computeCost(actor, time=time_cost)

    def preconditionsMet(self, (actor, obj), world):
        try:
            if actor['coordinates'] != obj['coordinates']:
                return False
        except KeyError:
            return False
        if 'use_requires' in obj:
            inventory = actor.get('inventory', [])
            for item in (world['things'][x] for x in inventory):
                if obj['use_requires'] in item['types']:
                    return True
        return False

    def effectEffects(self, (actor, obj), world):
        if 'use_requires' in obj:
            inventory = actor.get('inventory', [])
            for item in (world['things'][x] for x in inventory):
                if obj['use_requires'] in item:
                    inventory.remove(item['id'])
                    break
        if 'coordinates' in obj['effect']:
            actor['coordinates'] = obj['effect']['coordinates']



def formatPath(path):
    return ' --> '.join(str(x) for x in path)

def runSimulation():
    planner = Planner()
    planner.all_actions.append(Walk())
    planner.all_actions.append(Ride())
    planner.all_actions.append(Take())
    planner.all_actions.append(Drop())
    planner.all_actions.append(Buy())
    planner.all_actions.append(Use())

    world = {
        'things': {},
        'time': 0,
    }

    def addThing(id, x):
        x['id'] = id
        world['things'][id] = x
        return x

    addThing('bob', {
        'types': ['biped'],
        'inventory': [],
        'walking_speed': 1/3600.0,
        'coordinates': 0,
        'money': 10,
        'morality': 1,
        'money_value': 10,
    })
    addThing('home', {
        'types': ['location'],
        'coordinates': 0,
    })
    addThing('work', {
        'types': ['location'],
        'coordinates': 5,
    })
    addThing('shed', {
        'types': ['location'],
        'coordinates': -1,
    })
    addThing('red bike', {
        'types': ['rideable', 'takeable'],
        'speed': 3/3600.0,
        'coordinates': -1,
    })
    addThing('train station A', {
        'types': ['useable', 'trainstation'],
        'coordinates': -1,
        'effect': {
            'coordinates': 5,
            'speed': 80/3600.0,
        },
        'use_requires': 'trainticket',
    })
    addThing('trainticket1', {
        'types': ['takeable', 'trainticket'],
        'price': 1,
        'coordinates': 0,
    })

    # for x in planner.possibleNextActions(bob, world):
    #     print x

    def check(world):
        actor = world['things']['bob']
        return actor['coordinates'] == world['things']['work']['coordinates']

    goal = Goal(check)

    for x in planner.bestPathsToGoal('bob', world, goal):
        print formatPath(x)




if __name__ == '__main__':
    runSimulation()
