"""
Based on http://guineashots.com/2014/09/24/implementing-a-behavior-tree-part-1/
"""

import weakref
import time
import termcolor

OK, FAIL, RUNNING, ERR = range(4) 


class Blackboard(object):

    def __init__(self):
        self._global_memory = {}
        self._tree_memories = weakref.WeakKeyDictionary()

    def memory(self, tree=None, node=None):
        memory = self._global_memory
        if tree:
            memory = self._tree_memories.setdefault(tree, {
                '_node_memory': weakref.WeakKeyDictionary(),
            })
            if node:
                memory = memory['_node_memory'].setdefault(node, {})
        return memory

def silentDebugger(*args):
    pass


class TickContext(object):

    node_count = 0

    def __init__(self, tree, target, blackboard, debug=silentDebugger):
        self.open_nodes = []
        self.tree = tree
        self.target = target
        self.blackboard = blackboard
        self.debug = debug

    def nodeEntered(self, node):
        self.node_count += 1
        self.open_nodes.append(node)
        self.debug(self, 'nodeEntered', node)

    def nodeOpened(self, node):
        self.debug(self, 'nodeOpened', node)

    def nodeTicked(self, node):
        self.debug(self, 'nodeTicked', node)

    def nodeClosed(self, node):
        self.open_nodes.remove(node)
        self.debug(self, 'nodeClosed', node)

    def nodeExited(self, node):
        self.debug(self, 'nodeExited', node)



class BehaviorTree(object):

    def __init__(self, root, debug=silentDebugger):
        self.root = root
        self.debug = debug

    def tick(self, target, blackboard):
        self.debug(self, 'tick', target, blackboard)
        ctx = TickContext(tree=self, target=target, blackboard=blackboard,
            debug=self.debug)
        self.root.run(ctx)

        # close nodes that were open at the beginning, but aren't now
        memory = blackboard.memory(self)
        last_open_nodes = memory.get('open_nodes', set())
        this_open_nodes = set(ctx.open_nodes)

        for node in (last_open_nodes - this_open_nodes):
            self.debug(self, 'closing', node)
            node.close(ctx)

        memory['open_nodes'] = this_open_nodes
        memory['node_count'] = ctx.node_count


class _BaseNode(object):

    name = None

    def run(self, ctx):
        memory = self.memory(ctx)
        self._enter(ctx)
        self._open(ctx, memory)
        status = self._tick(ctx)
        if status != RUNNING:
            self._close(ctx, memory)
        self._exit(ctx)
        return status

    def memory(self, ctx):
        return ctx.blackboard.memory(ctx.tree, self)

    def _enter(self, ctx):
        ctx.nodeEntered(self)
        self.enter(ctx)

    def _open(self, ctx, memory):
        if not memory.get('is_open', False):
            ctx.nodeOpened(self)
            memory['is_open'] = True
            self.open(ctx)

    def _tick(self, ctx):
        ctx.nodeTicked(self)
        return self.tick(ctx)

    def _close(self, ctx, memory):
        ctx.nodeClosed(self)
        memory.pop('is_open', None)
        self.close(ctx)

    def _exit(self, ctx):
        ctx.nodeExited(self)
        self.exit(ctx)

    def enter(self, ctx):
        pass

    def open(self, ctx):
        pass

    def tick(self, ctx):
        pass

    def close(self, ctx):
        pass

    def exit(self, ctx):
        pass

    def _getName(self):
        return self.name or self.__class__.__name__

    def __repr__(self):
        return '<{0}>'.format(self._getName())


class Sequence(_BaseNode):
    """
    I fail on the first failure of my children and only succeed
    if all my children succeed.
    """

    def __init__(self, name=None, children=None):
        self.name = name
        self.children = children or []

    def tick(self, ctx):
        for c in self.children:
            status = c.run(ctx)
            if status != OK:
                return status
        return OK

class MemSequence(_BaseNode):
    """
    I do what the L{Sequence} does but I also remember what last
    ran/succeeded and start from there instead of at the first child.
    """
    
    def __init__(self, name=None, children=None):
        self.name = name
        self.children = children or []

    def open(self, ctx):
        self.memory(ctx)['running_child_idx'] = 0

    def tick(self, ctx):
        memory = self.memory(ctx)
        idx = memory['running_child_idx']
        for i,c in enumerate(self.children[idx:]):
            status = c.run(ctx)
            if status != OK:
                if status == RUNNING:
                    memory['running_child_idx'] = i + idx
                return status
        return OK


class Priority(_BaseNode):
    """
    I succeed on the first success of children and only fail
    if all my children fail.
    """

    def __init__(self, name=None, children=None):
        self.name = name
        self.children = children or []

    def tick(self, ctx):
        for c in self.children:
            status = c.run(ctx)
            if status != FAIL:
                return status
        return FAIL


class MemPriority(_BaseNode):
    """
    I do what the L{Priority} does but I also remember what last
    ran/succeeded and start from there instead of at the first child.
    """
    
    def __init__(self, name=None, children=None):
        self.name = name
        self.children = children or []

    def open(self, ctx):
        self.memory(ctx)['running_child_idx'] = 0

    def tick(self, ctx):
        memory = self.memory(ctx)
        idx = memory['running_child_idx']
        for i,c in enumerate(self.children[idx:]):
            status = c.run(ctx)
            if status != FAIL:
                if status == RUNNING:
                    memory['running_child_idx'] = i + idx
                return status
        return FAIL



#-----------------------------------------------------------
# Actions
#-----------------------------------------------------------

class WaitAction(_BaseNode):

    def __init__(self, seconds):
        self.seconds = seconds

    def open(self, ctx):
        self.memory(ctx)['end_time'] = time.time() + self.seconds

    def tick(self, ctx):
        now = time.time()
        end = self.memory(ctx)['end_time']

        if now >= end:
            return OK
        return RUNNING


class SaySomething(_BaseNode):

    def __init__(self, saying):
        self.saying = saying

    def tick(self, ctx):
        print self.saying
        return OK


def debugPrinter(*args):
    print termcolor.colored(' '.join(map(str, args)), attrs=['dark'])


if __name__ == '__main__':
    bt = BehaviorTree(Sequence('look busy', [
        WaitAction(3),
        SaySomething('Hello, world?'),
    ]), debug=debugPrinter)
    agent = object()
    blackboard = Blackboard()
    while True:
        bt.tick(agent, blackboard)
        time.sleep(0.01)

