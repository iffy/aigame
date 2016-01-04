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


class Arg(object):

    def __init__(self, name, type=None, has_attr=None, had_by=None):
        self.name = name
        self.type = type
        self.has_attr = has_attr
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
        if self.has_attr is not None:
            conds.append(self.has_attr in thing)
        if self.had_by is not None:
            conds.append(hasThing(current_args[self.had_by], thing))
        return all(conds)


class Action(object):

    name = None
    args = []

    def bind(self, arg_ids):
        if isinstance(arg_ids, dict):
            arg_ids = [arg_ids[arg.name]['id'] for arg in self.args]
        return BoundAction(self, arg_ids)

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

    def __repr__(self):
        name = self.name or (self.__class__.__name__)
        return '<Action:{0}>'.format(name)


class BoundAction(object):

    def __init__(self, action, arg_ids):
        self._action = action
        self._arg_ids = arg_ids

    def _callMethod(self, name, world):
        real_args = [world['things'][x] for x in self._arg_ids]
        return getattr(self._action, name)(real_args, world)

    def preconditionsMet(self, world):
        return self._callMethod('preconditionsMet', world)

    def effectEffects(self, world):
        return self._callMethod('effectEffects', world)

    def __repr__(self):
        return '<BoundAction {0!r} {1!r}>'.format(self._action, self._arg_ids)


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


class Planner(object):

    def __init__(self):
        self.all_actions = []

    def possiblePathsToGoal(self, actor_id, world, goal_func, args=None, kwargs=None):
        """
        Return all possible paths to a particular goal state.

        @param goal_func: A function that should return True if the goal is achieved,
            and False if it is not achieved.  Called like this:
            goal_func(future_actor, future_world, *args, **kwargs)
        """
        args = args or ()
        kwargs = kwargs or {}
        tree = self.buildActionTree(actor_id, world)

        # find end states
        goal_nodes = []
        for x in tree.walk():
            actor = x.data['things'][actor_id]
            if goal_func(actor, x.data, *args, **kwargs):
                goal_nodes.append(x)
        
        for path, node in tree.listPaths():
            if node in goal_nodes:
                yield path


    def buildActionTree(self, actor_id, world):
        """

        """
        starting_world = copy.deepcopy(world)
        done = []
        tree = Node(starting_world)
        work = [tree]
        while work:
            old_node = work.pop(0)
            if old_node.data in done:
                # old_node already done
                continue
            done.append(old_node.data)

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
        Arg('actor', type='biped'),
        Arg('dest', type='location'),
    ]
    
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
    
    def preconditionsMet(self, (actor, rideable, dest), world):
        return actor['coordinates'] != dest['coordinates']

    def effectEffects(self, (actor, rideable, dest), world):
        actor['coordinates'] = dest['coordinates']


class Take(Action):

    args = [
        Arg('actor', has_attr='inventory'),
        Arg('obj', type='takeable'),
    ]

    def preconditionsMet(self, (actor, obj), world):
        try:
            return actor['coordinates'] == obj['coordinates']
        except KeyError:
            return False

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


def runSimulation():
    planner = Planner()
    planner.all_actions.append(Walk())
    planner.all_actions.append(Ride())
    planner.all_actions.append(Take())
    planner.all_actions.append(Drop())

    world = {
        'things': {},
    }

    def addThing(id, x):
        x['id'] = id
        world['things'][id] = x
        return x

    addThing('bob', {
        'types': ['biped'],
        'inventory': [],
        'walking_speed': 1,
        'coordinates': 0,
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
        'speed': 2,
        'coordinates': -1,
    })

    # for x in planner.possibleNextActions(bob, world):
    #     print x

    def goal(actor, world):
        return actor['coordinates'] == world['things']['work']['coordinates']

    for x in planner.possiblePathsToGoal('bob', world, goal):
        print x




if __name__ == '__main__':
    runSimulation()
