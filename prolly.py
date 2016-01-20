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
       | term:head ws 'if' ws term:body -> Rule(head, body)
       | term:head -> Rule(head, TRUE)
'''


from functools import wraps

call_count = 0

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

    @logTruthy
    def match(self, other):
        if isinstance(other, Atom):
            if self.value == other.value:
                return {self.value: other.value}
        elif isinstance(other, Var):
            return {other.name: self.value}
        return {}

    def normalizeVars(self, db):
        return self

    def substitute(self, mapping):
        return self


class Term(object):

    def __init__(self, *args):
        self.args = args

    @property
    def arity(self):
        return len(self.args)

    @logTruthy
    def match(self, query, brain):
        """
        Return a dict whose keys are items in my args and values
        are what my args should be changed to to match the given query.
        """
        match_mapping = {}
        for me,q in zip(self.args, query.args):
            m = me.match(q)
            if not m:
                # mismatch
                return {}
            match_mapping.update(m)
        return match_mapping

    @logTruthy
    def substitute(self, mapping):
        """
        Create a new Term with my args replaced according to
        the mapping.  Typically, the mapping is something
        returned by my C{match} function.
        """
        return Term(*[x.substitute(mapping) for x in self.args])

    def normalizeVars(self, db):
        return Term(*[x.normalizeVars(db) for x in self.args])

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
        return '<Var({0!r}) {1}>'.format(self.name, id(self))

    def __str__(self):
        return self.name

    def match(self, query, brain=None):
        print 'VAR MATCH', self, query
        return {self:query}

    @logTruthy
    def substitute(self, mapping):
        print 'mapping', mapping, self
        return mapping.get(self, self)

    def normalizeVars(self, db):
        return db.setdefault(self.name, self)


class Conflict(Exception):
    pass

class And(object):

    def __init__(self, parts):
        self.parts = parts

    def __repr__(self):
        return 'And({0!r})'.format(self.parts)

    def __str__(self):
        return ' and '.join(map(str, self.parts))

    @logTruthy
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
        return self._findPartialMatches(self.parts, {}, brain)

    def _findPartialMatches(self, args, context, brain):
        print '_findPartialMatches', args, brain
        arg = args[0].substitute()
        rest = args[1:]
        for x in brain.parsedQuery(arg):
            print 'x', x
            if rest:
                print 'rest', rest
                for y in self._findPartialMatches(rest, brain):
                    try:
                        v = self._mergeWithoutOverwriting(x, y)
                        print 'yielding', v
                        yield v
                    except Conflict:
                        pass
            else:
                print 'no rest, yielding', x
                yield x

    def _mergeWithoutOverwriting(self, a, b):
        """
        Merge every new value in b into a
        """
        a_copy = a.copy()
        for k, v in b.items():
            if k in a_copy and a_copy[k] != v:
                raise Conflict('Not the same', k, a_copy[k], v)
            a_copy[k] = v
        return a_copy


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


class _TRUE(Term):

    def __str__(self):
        return 'true'

    def __repr__(self):
        return '<TRUE>'

    def substitute(self, mapping):
        return self

    def normalizeVars(self, db):
        return self

    def findMatches(self, brain):
        yield {}


TRUE = _TRUE()

parser = parsley.makeGrammar(grammar, {
    'Atom': Atom,
    'Term': Term,
    'Var': Var,
    'Rule': Rule,
    'And': And,
    'TRUE': TRUE,
})


class Brain(object):

    def __init__(self):
        self._rules = []

    def add(self, rule):
        """
        Add a fact to this brain.
        """
        print 'ADD', rule
        rule = parser(rule).rule().normalizeVars()
        self._rules.append(rule)

    def query(self, query):
        """
        Query the brain.
        """
        print 'query', query
        query = parser(query).rule().head
        print 'parse', query
        print repr(query)
        return self.parsedQuery(query)

    def parsedQuery(self, query):
        for rule in self._rules:
            print ''
            print 'RULE', rule
            head_match = rule.head.match(query, self)
            if head_match:
                print 'head_match', head_match
                mapped_body = rule.body.substitute(head_match)
                print 'mapped_body', mapped_body
                for match in mapped_body.findMatches(self):
                    print 'match', match
                    match.update(head_match)
                    yield match
            


