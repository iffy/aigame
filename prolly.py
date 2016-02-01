import parsley
from termcolor import colored

grammar = '''
tchar = letterOrDigit:x ?(x in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-') -> x
atom = letter:first <tchar*>:rest ?(first == first.lower()) -> Atom(first + rest)
var = letter:first <tchar*>:rest ?(first == first.upper()) -> Var(first + rest)
ws = ' '*

simple_term = atom | var
term = simple_term:x -> x
    | '(' term_list:x ')' -> Term(*x)
term_list = (term:first (ws ',' ws term)*:rest -> [first] + rest) | -> []

and_list = (term:first (ws 'and' ws term)*:rest -> [first] + rest) | -> []

rule = term:head ws 'if' ws and_list:body -> Rule(head, And(body))
       | term:head -> Rule(head, TRUE)
'''


from functools import wraps

call_count = 0

def log(*args):
    print ' '.join(map(str, args))

def reverseDict(d):
    return {v:k for k,v in d.items()}

def _mergeWithoutOverwriting(a, b):
    """
    Merge every new value in b into a
    """
    a_copy = a.copy()
    for k, v in b.items():
        if k in a_copy and a_copy[k] != v:
            raise Conflict('Not the same', k, a_copy[k], v)
        a_copy[k] = v
    return a_copy

def logTruthy(method):
    @wraps(method)
    def func(self, *args, **kwargs):
        global call_count
        call = '{cls}.{method} {self} {args}'.format(
            cls=self.__class__.__name__,
            method=method.__name__,
            self=self,
            args=args)
        this_count = call_count
        call_count += 1
        print colored('{0}: {1}'.format(this_count, call), 'yellow', attrs=['dark'])
        r = method(self, *args, **kwargs)
        ret_string = '{count}: {call}\n  -> {r}'.format(
            count=this_count, call=call, r=r)
        if r:
            print colored(ret_string, 'green')
        else:
            print colored(ret_string, attrs=['dark'])
        return r
    return func


class Atom(object):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'Atom({0!r})'.format(self.value)

    def __str__(self):
        return str(self.value)

    def match(self, other):
        """
        Return a dictionary that maps 
        """
        if isinstance(other, Atom):
            if self.value == other.value:
                return {self: other}
        elif isinstance(other, Var):
            return {other: self}
        return {}

    def normalizeVars(self, db):
        return self

    def substitute(self, mapping):
        return self

    def getValue(self):
        return self.value

    def listVars(self):
        return []


class Term(object):

    def __init__(self, *args):
        self.args = args

    @property
    def arity(self):
        return len(self.args)

    def match(self, query, brain):
        """
        Return a dict whose keys are items in my args and values
        are what my args should be changed to to match the given query.
        """
        match_mapping = {}
        if self.arity != query.arity:
            # doesn't match the number of args
            return {}
        for me,q in zip(self.args, query.args):
            m = me.match(q)
            if not m:
                # mismatch
                return {}
            match_mapping.update(m)
        return match_mapping

    def substitute(self, mapping):
        """
        Create a new Term with my args replaced according to
        the mapping.  Typically, the mapping is something
        returned by my C{match} function.
        """
        return Term(*[x.substitute(mapping) for x in self.args])

    def normalizeVars(self, db):
        return Term(*[x.normalizeVars(db) for x in self.args])

    def listVars(self):
        ret = []
        for arg in self.args:
            ret.extend(arg.listVars())
        return ret 

    def __repr__(self):
        return 'Term{0!r}'.format(self.args)

    def __str__(self):
        if len(self.args) == 1:
            return str(self.args[0])
        else:
            return '({0})'.format(', '.join(map(str, self.args)))


class Var(object):

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Var{0} {1}>'.format(self.name, hex(id(self)))

    def __str__(self):
        return self.name

    def match(self, query, brain=None):
        return {self:query}

    def substitute(self, mapping):
        return mapping.get(self, self)

    def normalizeVars(self, db):
        return db.setdefault(self.name, self)

    def listVars(self):
        return [self]

    def getValue(self):
        return self.name


class Conflict(Exception):
    pass

class And(object):

    def __init__(self, parts):
        self.parts = parts

    def __repr__(self):
        return 'And({0!r})'.format(self.parts)

    def __str__(self):
        return ' and '.join(map(str, self.parts))

    def substitute(self, mapping):
        """
        Make a copy of myself with variables changed.
        """
        return And([part.substitute(mapping) for part in self.parts])

    def normalizeVars(self, db):
        return And([x.normalizeVars(db) for x in self.parts])

    def findMatches(self, brain):
        """
        Find all the matches
        """
        return self._findPartialMatches(self.parts, brain)

    def _findPartialMatches(self, args, brain):
        head = args[0]
        tail = args[1:]
        for match in brain.parsedQuery(head):
            if tail:
                mapped_tail = [x.substitute(match) for x in tail]
                for tail_match in self._findPartialMatches(mapped_tail, brain):
                    full_match = match.copy()
                    full_match.update(tail_match)
                    yield full_match
            else:
                yield match

    def listVars(self):
        ret = []
        for arg in self.parts:
            ret.extend(arg.listVars())
        return ret


class Rule(object):

    def __init__(self, head, body):
        self.head = head
        self.body = body

    def __repr__(self):
        return 'Rule({0!r}, {1!r})'.format(self.head, self.body)

    def __str__(self):
        return '{0} if {1}'.format(self.head, self.body)

    def normalizeVars(self, db=None):
        db = db or {}
        head = self.head.normalizeVars(db)
        body = self.body.normalizeVars(db)
        return Rule(head, body)

    def listVars(self):
        return self.head.listVars() + self.body.listVars()


class _TRUE(Term):

    def __str__(self):
        return 'true'

    def __repr__(self):
        return '<TRUE>'

    def substitute(self, mapping):
        return self

    def normalizeVars(self, db):
        return self


TRUE = _TRUE()

parser = parsley.makeGrammar(grammar, {
    'Atom': Atom,
    'Term': Term,
    'Var': Var,
    'Rule': Rule,
    'And': And,
    'TRUE': TRUE,
})


def humanize(d):
    return {k.getValue():v.getValue() for k,v in d.items()}


def reduceMatchToQuery(match, query):
    """
    Reduce the elemtns in a match to the variables in a query.
    """
    var_names = [x.name for x in query.listVars()]
    return {k:v for k,v in match.items() if k in var_names}



class Brain(object):

    def __init__(self):
        self._rules = []

    def add(self, rule):
        """
        Add a fact to this brain.
        """
        rule = parser(rule).rule().normalizeVars()
        self._rules.append(rule)

    def query(self, query):
        """
        Query the brain.
        """
        print 'query', query
        query = parser(query).rule().normalizeVars().head
        print 'parsed -> ', query
        found = set()
        for match in self.parsedQuery(query):
            print '**', humanize(match)
            ret = reduceMatchToQuery(humanize(match), query)
            h = tuple(ret.items())
            if h in found:
                continue
            found.add(h)
            yield ret

    def parsedQuery(self, query):
        """
        Query the brain using an already-parsed-into-python-objects
        query.
        """
        encountered = set()
        for rule in self._rules:
            mapping = rule.head.match(query, self)
            if not mapping:
                continue

            h = (rule,) + tuple(sorted(humanize(mapping).items()))
            if h in encountered:
                print 'SKIP DUPE', rule, mapping
                continue
            encountered.add(h)

            log('\nQUERY', query)
            log('  MATCHES', rule)
            log('  FOR', humanize(mapping))
            mapped_body = rule.body.substitute(mapping)
            log('  MAKING', mapped_body)
            if isinstance(mapped_body, _TRUE):
                log('  TRUE', mapping)
                yield mapping
            else:
                for match in mapped_body.findMatches(self):
                    log('  match', match)
                    res = _mergeWithoutOverwriting(mapping, match)
                    log('  res', res)
                    yield res


