# Using https://curiosity-driven.org/prolog-interpreter#glue as an example implementation
from functools import wraps
from termcolor import colored

level = 0
def logmethod(f):
    """
    Log a normal method call
    """
    @wraps(f)
    def func(self, *args, **kwargs):
        global level
        name = repr(self) + '.' + func.__name__
        arg_string = map(repr, args)
        for k,v in kwargs.items():
            arg_string.append('{0}={1}'.format(k,v))
        print '{0}{1}({2})'.format(
            colored('|   '*level, attrs=['dark']),
            name,
            ', '.join(arg_string))
        level += 1
        result = f(self, *args, **kwargs)
        level -= 1
        print '{0}{1}'.format(
            colored('|   '*level, attrs=['dark']),
            colored(repr(result), 'cyan'))
        return result
    return func

def loggenmethod(f):
    """
    Log a generator-returning call
    """
    @wraps(f)
    def func(self, *args, **kwargs):
        global level
        name = repr(self) + '.' + func.__name__
        arg_string = map(str, args)
        for k,v in kwargs.items():
            arg_string.append('{0}={1}'.format(k,v))
        prefix = '{0}({1})'.format(name, ', '.join(arg_string))
        return GenLogger(prefix, f(self, *args, **kwargs))
    return func


class GenLogger(object):

    def __init__(self, prefix, iterator):
        self.iterator = iterator
        self.prefix = prefix
        self.i = 0

    def __iter__(self):
        return self

    def next(self):
        global level
        print '{pre}{i} {prefix}'.format(
            pre=colored('|   '*level, attrs=['dark']),
            prefix=self.prefix,
            i=colored(self.i, 'yellow'))
        level += 1
        try:
            result = self.iterator.next()
            level -= 1
            print '{pre}{i} {result} {prefix}'.format(
                pre=colored('|   '*level, attrs=['dark']),
                result=colored(result, 'cyan'),
                prefix=self.prefix,
                i=colored(self.i, 'yellow'))
        except StopIteration:
            level -= 1
            print '{pre}{i}'.format(
                pre=colored('|   '*level, attrs=['dark']),
                i=colored(self.i, 'red'),
                prefix=self.prefix,
                stop=colored('END', 'red', attrs=['dark']))
            raise
            
        self.i += 1
        return result


def log(*args):
    print '{0}{1}'.format(
            colored('|   '*level, attrs=['dark']),
            colored(' '.join(map(str, args)), attrs=['dark']))


def _mergeBindings(b1, b2):
    """
    Merge two sets of bindings.

    @param b1: Accumulated result
    @param b2: Results to merge in
    """
    # XXX explain this, eh?
    if b1 is None or b2 is None:
        return None
    # start with the accumulated result
    result = {k:v for k,v in b1.items()}
    for k,v in b2.items():
        other = result.get(k, None)
        if other is not None:
            sub = other.match(v)
            if sub is None:
                # conflict
                log('CONFLICT')
                return None
            else:
                for k,v in sub.items():
                    result[k] = v
        else:
            result[k] = v
    return result


class Var(object):

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'Var({0!r})'.format(self.name)

    def __str__(self):
        return self.name

    @logmethod
    def match(self, other):
        """
        Return a dictionary mapping this Var to other if
        they are different.
        """
        # XXX explain this, eh?
        bindings = {}
        if other != self:
            bindings[self] = other
        return bindings

    @logmethod
    def sub(self, bindings):
        """
        Return what I represent in the given bindings.
        """
        # XXX explain this, eh?
        value = bindings.get(self)
        if value:
            return value.sub(bindings)
        log('no matching binding found')
        return self

    def value(self):
        return self.name


class Term(object):

    def __init__(self, functor, args=None):
        self.functor = functor
        self.args = args or []

    def __repr__(self):
        if self.args:
            return 'Term({0!r}, {1!r})'.format(self.functor, self.args)
        else:
            return 'Term({0!r})'.format(self.functor)

    def __str__(self):
        if self.args:
            return '{0}({1})'.format(self.functor, ', '.join(map(str, self.args)))
        else:
            return self.functor

    def value(self):
        return self.functor

    def match(self, other):
        # XXX explain this, eh?
        if isinstance(other, Term):
            if self.functor != other.functor:
                return None
            if len(self.args) != len(other.args):
                return None
            d = []
            for (a,b) in zip(self.args, other.args):
                d.append(a.match(b))
            return reduce(_mergeBindings, d, {})
        return other.match(self)

    @logmethod
    def sub(self, bindings):
        # XXX explain this, eh?
        return Term(self.functor, [x.sub(bindings) for x in self.args])

    def query(self, brain):
        for x in brain.query(self):
            yield x


class TRUE(Term):

    def __init__(self):
        self.functor = None
        self.args = []

    def sub(self, bindings):
        return self

    def query(self, brain):
        yield self

    def __repr__(self):
        return 'TRUE()'

    def __str__(self):
        return 'True'

    def value(self):
        return True


class Trueness(Term):

    def __init__(self, trueness=1):
        self.functor = None
        self.args = []
        self.trueness = trueness

    def sub(self, bindings):
        return self

    def query(self, brain):
        yield self

    def __repr__(self):
        return 'Trueness({0!r})'.format(self.trueness)

    def __str__(self):
        return 'True{0}'.format(self.trueness)

    def value(self):
        return self.trueness


class Rule(object):

    def __init__(self, head, body):
        self.head = head
        self.body = body

    def __repr__(self):
        return '{0!r} :- {1!r}.'.format(self.head, self.body)

    def __str__(self):
        return '{0} :- {1}.'.format(str(self.head), str(self.body))


class Conjunction(Term):

    def __init__(self, args):
        self.functor = None
        self.args = args

    @logmethod
    def sub(self, bindings):
        # XXX explain this, eh?
        return Conjunction([x.sub(bindings) for x in self.args])

    @loggenmethod
    def query(self, brain):
        # XXX explain this, eh?
        return self._getSolutions(brain, {}, self.args)

    def _getSolutions(self, brain, bindings, args):
        if not args:
            log('no args')
            yield self.sub(bindings)
        else:
            arg = args[0]
            log('arg', arg)
            log('bindings', bindings)
            goal = arg.sub(bindings)
            log('goal', goal)
            for item in brain.query(goal):
                log('item', item)
                match = arg.match(item)
                log('match', match)
                unified = _mergeBindings(match, bindings)
                log('unified', unified)
                if unified:
                    for x in self._getSolutions(brain, unified, args[1:]):
                        yield x

    def __repr__(self):
        return ', '.join(map(repr, self.args))

    def __str__(self):
        return ', '.join(map(str, self.args))


class Brain(object):

    def __init__(self):
        self.rules = []

    def addFact(self, functor, args):
        term_args = []
        for arg in args:
            if not isinstance(arg, Term):
                arg = Term(arg)
            term_args.append(arg)

        body = TRUE()
        self.addRule(Rule(Term(functor, term_args), body))

    def addRule(self, rule):
        self.rules.append(rule)

    @loggenmethod
    def query(self, goal):
        for rule in self.rules:
            match = rule.head.match(goal)
            if match:
                head = rule.head.sub(match)
                log('head', head)
                body = rule.body.sub(match)
                log('body', body)
                for item in body.query(self):
                    yield head.sub(body.match(item))

    @loggenmethod
    def pyquery(self, functor, args):
        """
        Query, but return native Python types instead of classes/objects
        """
        goal = Term(functor, args)
        for x in self.query(goal):
            matched = goal.match(x)
            ret = {}
            for k,v in matched.items():
                ret[k.value()] = v.value()
            yield ret


# importance of a fact
# perceived truthfulness of a fact
# mutation of a fact
# forgetting a fact
