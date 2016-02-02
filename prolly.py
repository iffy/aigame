import parsley
import itertools
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
    a_copy = {}
    b_copy = {k:v for k,v in b.items()}
    for k,v in a.items():
        if v in b_copy:
            a_copy[k] = b_copy.pop(v)
        else:
            a_copy[k] = v
    for k, v in b_copy.items():
        if k in a_copy and a_copy[k] != v:
            if a_copy[k] in b_copy:
                a_copy[k] = b_copy[a_copy[k]]
                continue
            else:
                raise Conflict('Not the same merging', a, b, k)
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
        return '<{0}>'.format(self.value)

    def __str__(self):
        return repr(self)

    def __eq__(self, other):
        if isinstance(other, Atom):
            return self.value == other.value
        return False

    def __ne__(self, other):
        return not(self == other)

    def __hash__(self):
        return hash(self.value)

    def matches(self, other, brain):
        """
        Generate the bindings that map other to self.
        """
        if isinstance(other, Atom):
            if self.value == other.value:
                yield {other: self}
        elif isinstance(other, Var):
            yield {self: other}

    def normalizeVars(self, db):
        return self

    def substitute(self, mapping):
        return self

    def getValue(self):
        return self.value

    def listVars(self):
        return []


def combineDicts(dicts):
    ret = {}
    for d in dicts:
        ret = _mergeWithoutOverwriting(ret, d)
    return ret


class Term(object):

    def __init__(self, *args):
        self.args = args

    @property
    def arity(self):
        return len(self.args)

    def matches(self, other, brain):
        """
        Generate the bindings keys are items in my args and values
        are what my args should be changed to to match the given other.
        """
        if self.arity != other.arity:
            # doesn't match the number of args
            return
        match_gens = []
        for me, q in zip(self.args, other.args):
            match_gens.append(me.matches(q, brain))

        for matches in itertools.product(*match_gens):
            try:
                yield combineDicts(matches)
            except Conflict:
                pass

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
        return '({0})'.format(', '.join(map(str, self.args)))


class Var(object):

    count = 0

    def __init__(self, name):
        self.name = name
        Var.count += 1
        self.number = Var.count

    def __repr__(self):
        return '<{0}.{1}>'.format(self.name, self.number)

    def __str__(self):
        return self.name

    def matches(self, other, brain):
        yield {self: other}

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

    def query(self, brain):
        """
        Find all the matches for a query.
        """
        return self._partialQuery(self.parts, brain)

    def _partialQuery(self, args, brain):
        head = args[0]
        tail = args[1:]
        for match in brain.parsedQuery(head):
            if tail:
                mapped_tail = [x.substitute(match) for x in tail]
                for tail_match in self._partialQuery(mapped_tail, brain):
                    try:
                        full_match = _mergeWithoutOverwriting(match, tail_match)
                    except Conflict:
                        log('  conflict')
                        log('  match', match)
                        log('  tail ', tail_match)
                        continue
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
        return 'true/0'

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
        log('query', query)
        query = parser(query).rule().normalizeVars().head
        log('parsed -> ', repr(query))
        for match in self.parsedQuery(query):
            log(colored('** {0}'.format(humanize(match)), 'cyan'))
            ret = humanize(match)
            yield ret

    def unique(self, gen):
        encountered = set()
        for x in gen:
            h = hash(tuple(sorted(x.items())))
            if h in encountered:
                continue
            encountered.add(h)
            yield x

    def parsedQuery(self, query):
        """
        Query the brain using an already-parsed-into-python-objects
        query.
        """
        return self.unique(self._parsedQuery(query))

    def _parsedQuery(self, query):
        for rule in self._rules:
            for mapping in rule.head.matches(query, self):
                log('\nQUERY', repr(query))
                log('  MATCHES', repr(rule))
                log('  FOR', mapping)
                if isinstance(rule.body, _TRUE):
                    log('  TRUE', mapping)
                    ret = reverseDict(mapping)
                    log('   ret', ret)
                    yield ret
                else:
                    #mapped_body = rule.body.substitute(mapping)
                    #log('  MAKING', repr(mapped_body))
                    for match in rule.body.query(self):
                        log(colored('\nQUERY {0!r}'.format(query), attrs=['dark']))
                        log(colored('  RULE  {0!r}'.format(rule), attrs=['dark']))
                        log('  mapping', mapping)
                        rev_map = reverseDict(mapping)
                        log('  rev    ', rev_map)
                        log('  match  ', match)
                        
                        ret = {}
                        # convert match back using mapping
                        try:
                            for k,v in list(rev_map.items()):
                                if isinstance(v, Var):
                                    match_v = match[v]
                                    if isinstance(k, Var):
                                        ret[k] = match_v
                                    elif match_v != k:
                                        raise Conflict("Can't merge", rev_map, match)
                                elif isinstance(k, Var):
                                    ret[k] = v
                        except Conflict as e:
                            log('  CONFLICT', e)
                            continue

                                
                        log('  ret    ', ret)
                        yield ret

                        # rmatch = {}
                        # for k,v in match.items():
                        #     if isinstance(k, Var):
                        #         rmatch[rev_map[k]] = v
                        # log('  rmatch ', rmatch)

                        # merge match with existing
                        # merged = _mergeWithoutOverwriting(mapping, match)
                        # log('  merged ', merged)
                        
                        # trim the mapping
                        # for k,v in list(match.items()):
                        #     if k not in mapping.values():
                        #         match.pop(k)
                        #     elif not isinstance(k, Var):
                        #         match.pop(k)
                        # yield match


