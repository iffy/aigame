# Using https://curiosity-driven.org/prolog-interpreter#glue as an example implementation
from functools import wraps
from termcolor import colored

level = 0
def logcall(f):
    """
    Log a normal function/method call
    """
    @wraps(f)
    def func(*args, **kwargs):
        global level
        print '{0}{1}{2}'.format(
            colored('| '*level, attrs=['dark']),
            func.__name__,
            args)
        level += 1
        result = f(*args, **kwargs)
        level -= 1
        print '{0}{1}'.format(
            colored('| '*level, attrs=['dark']),
            colored(result, 'cyan'))
        return result
    return func

def loggen(f):
    """
    Log a generator-returning call
    """
    @wraps(f)
    def func(*args, **kwargs):
        global level
        print '{0}{1}{2}'.format(
            colored('| '*level, attrs=['dark']),
            func.__name__,
            args)
        frozen_level = level
        level += 1
        i = 0
        for result in f(*args, **kwargs):
            print '{0}{1} {2}'.format(
                colored('| '*frozen_level, attrs=['dark']),
                colored(i, 'yellow'),
                colored(result, 'cyan'))
            i += 1
            yield result
        level -= 1
    return func

def log(*args):
    print '{0}{1}'.format(
            colored('| '*level, attrs=['dark']),
            colored(' '.join(map(str, args)), attrs=['dark']))


@logcall
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
    log('accumulated result', result)
    for k,v in b2.items():
        log('k', k, 'v', v)
        other = result.get(k, None)
        if other is not None:
            sub = other.match(v)
            if not sub:
                # conflict
                log('conflict')
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

    @logcall
    def match(self, other):
        # XXX explain this, eh?
        bindings = {}
        if self != other:
            bindings[self] = other
        return bindings

    @logcall
    def sub(self, bindings):
        # XXX explain this, eh?
        value = bindings.get(self)
        if value:
            return value.sub(bindings)
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

    def value(self):
        return self.functor

    @logcall
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

    @logcall
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

    def value(self):
        return True


class Rule(object):

    def __init__(self, head, body):
        self.head = head
        self.body = body

    def __repr__(self):
        return '{0!r} :- {1!r}.'.format(self.head, self.body)


class Conjunction(Term):

    def __init__(self, args):
        self.args = args

    @logcall
    def sub(self, bindings):
        # XXX explain this, eh?
        return Conjunction([x.sub(bindings) for x in self.args])

    def query(self, brain):
        # XXX explain this, eh?
        
        def solutions(index, bindings):
            arg = self.args[index]
            if not arg:
                yield self.sub(bindings)
            else:
                for item in brain.query(arg.sub(bindings)):
                    unified = _mergeBindings(arg.match(item), bindings)
                    if unified:
                        for x in solutions(index+1, unified):
                            yield x

        return solutions(0, {})

    def __repr__(self):
        return ', '.join(map(repr, self.args))


class Brain(object):

    def __init__(self):
        self.rules = []

    def addFact(self, functor, args, trueness=1):
        term_args = []
        for arg in args:
            if not isinstance(arg, Term):
                arg = Term(arg)
            term_args.append(arg)
        self.rules.append(Rule(Term(functor, term_args), TRUE())) 

    @loggen
    def _query(self, goal):
        for rule in self.rules:
            log('Rule', rule)
            match = rule.head.match(goal)
            log('match', match)
            if match:
                head = rule.head.sub(match)
                body = rule.body.sub(match)
                for item in body.query(self):
                    yield head.sub(body.match(item))

    @loggen
    def query(self, functor, args):
        goal = Term(functor, args)
        for x in self._query(goal):
            matched = goal.match(x)
            ret = {}
            for k,v in matched.items():
                ret[k.value()] = v.value()
            yield ret


# importance of a fact
# perceived truthfulness of a fact
# mutation of a fact
# forgetting a fact
