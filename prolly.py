import parsley
import itertools
from decimal import Decimal
from termcolor import colored

grammar = '''
tchar = letterOrDigit:x ?(x in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-') -> x
ws = ' '*

#----------------------------
# borrowed from http://parsley.readthedocs.org/en/latest/tutorial2.html
digits = <digit*>
digit1_9 = :x ?(x in '123456789') -> x

intPart = (digit1_9:first digits:rest -> first + rest) | digit
floatPart :sign :ds = <('.' digits)>:tail
                     -> Decimal(sign + ds + tail)
number = ('-' | -> ''):sign (intPart:ds (floatPart(sign ds)
                                               | -> int(sign + ds)))
#----------------------------

atom = 
    # number
    ( number:x -> Atom(x) )

    # string
    | letter:first <tchar*>:rest ?(first == first.lower()) -> Atom(first + rest)

#----------------------------
# variables
#----------------------------
var = letter:first <tchar*>:rest ?(first == first.upper()) -> Var(first + rest)

#----------------------------
# expressions
#----------------------------
expression = atom

#----------------------------
# tags
#----------------------------
tag_name = <tchar+>
tag = tag_name:key ws '=' ws atom:value -> (Var(key), value)
tag_list = (tag:first (ws ',' ws tag)*:rest -> [first] + rest) | -> []
tagging = ws '@' ws tag_list:x -> dict(x)

tag_prop = <tchar+>:key ws '(' ws expression:val ws ')' -> (key, val)
tag_prop_list = (tag_prop:first (ws ',' ws tag_prop)*:rest -> [first] + rest) | -> []
tag_prop_def = '@' ws tag_name:name ws tag_prop_list:props -> TagProps(name, dict(props))

#----------------------------
# terms
#----------------------------
simple_term = atom | var
term = simple_term:x -> x
    | '(' term_list:x ')' (tagging)?:tags -> Term(x, tags=tags)
term_list = (term:first (ws ',' ws term)*:rest -> [first] + rest) | -> []

and_list = (term:first (ws 'and' ws term)*:rest -> [first] + rest) | -> []

rule = term:head ws 'if' ws and_list:body -> Rule(head, And(body))
       | term:head -> Rule(head, TRUE)


clause = rule | tag_prop_def
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
        return NotImplemented

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

    def convertSpecialTerms(self, brain):
        return self

    def substitute(self, mapping):
        return self

    def humanValue(self):
        return self.value

    def listVars(self):
        return []


def combineDicts(dicts):
    ret = {}
    for d in dicts:
        ret = _mergeWithoutOverwriting(ret, d)
    return ret


class Term(object):

    def __init__(self, args, tags=None):
        self.args = args
        self.tags = tags or []

    @property
    def arity(self):
        return len(self.args)

    def matches(self, other, brain):
        """
        Generate the bindings keys are items in my args and values
        are what my args should be changed to to match the given other.
        """
        if isinstance(other, Term):
            return self.matches_Term(other, brain)
        elif isinstance(other, Var):
            return self.matches_Var(other, brain)

    def matches_Term(self, other, brain):
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

    def matches_Var(self, other, brain):
        yield {self: other}

    def clone(self, args):
        return self.__class__(args, tags=self.tags)

    def substitute(self, mapping):
        """
        Create a new Term with my args replaced according to
        the mapping.  Typically, the mapping is something
        returned by my C{match} function.
        """
        return self.clone([x.substitute(mapping) for x in self.args])

    def query(self, brain):
        return brain.parsedQuery(self)

    def normalizeVars(self, db):
        return self.clone([x.normalizeVars(db) for x in self.args])

    def convertSpecialTerms(self, brain):
        return brain.convertToSpecialTerm(
            self.clone([x.convertSpecialTerms(brain) for x in self.args]))

    def listVars(self):
        ret = []
        for arg in self.args:
            ret.extend(arg.listVars())
        return ret

    def humanValue(self):
        return tuple([x.humanValue() for x in self.args])

    def __repr__(self):
        s = '{0}{1!r}'.format(self.__class__.__name__, self.args)
        if self.tags:
            s += '@{0}'.format(self.tags)
        return s

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

    def convertSpecialTerms(self, brain):
        return self

    def listVars(self):
        return [self]

    def humanValue(self):
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

    def convertSpecialTerms(self, brain):
        return And([x.convertSpecialTerms(brain) for x in self.parts])

    def query(self, brain):
        """
        Find all the matches for a query.
        """
        return self._partialQuery(self.parts, brain)

    def _partialQuery(self, args, brain):
        head = args[0]
        tail = args[1:]
        print 'AND head', head
        print 'AND tail', tail
        for match in head.query(brain):
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

    def convertSpecialTerms(self, brain):
        head = self.head.convertSpecialTerms(brain)
        body = self.body.convertSpecialTerms(brain)
        return Rule(head, body)

    def listVars(self):
        return self.head.listVars() + self.body.listVars()

#------------------------------------------------------
# special terms

class _TRUE(Term):

    def __str__(self):
        return 'true/0'

    def __repr__(self):
        return '<TRUE>'

    def substitute(self, mapping):
        return self

    def normalizeVars(self, db):
        return self

TRUE = _TRUE([])

class SpecialTerm(Term):

    @classmethod
    def createFromTerm(cls, term):
        return cls(term.args)

class Not(SpecialTerm):
    """
    Negate stuff.
    """

    def query(self, brain):
        gen = brain.parsedQuery(self.args[1])
        try:
            gen.next()
            return
        except StopIteration:
            yield {}


class TagProps(object):

    def __init__(self, name, props):
        self.name = name
        self.props = props

    def __repr__(self):
        return '<TagProps {0} {1!r}>'.format(self.name, self.props)

grammar_bindings = {
    'Atom': Atom,
    'Term': Term,
    'Var': Var,
    'Rule': Rule,
    'And': And,
    'TRUE': TRUE,
    'Decimal': Decimal,
    'TagProps': TagProps,
}
PARSER = parsley.makeGrammar(grammar, grammar_bindings)


def humanize(d):
    return {k.humanValue():v.humanValue() for k,v in d.items()}


class Brain(object):

    def __init__(self):
        self._rules = []
        self._terms = {}
        self.tag_props = {}

        # default specials
        self.addTermType('not', Not.createFromTerm)

    def add(self, string):
        """
        Add a fact to this brain.
        """
        clause = PARSER(string).clause()
        if isinstance(clause, Rule):
            rule = clause.normalizeVars().convertSpecialTerms(self)
            self._rules.append(rule)
        elif isinstance(clause, TagProps):
            self.tag_props[clause.name] = clause.props
        else:
            raise Exception('Unknown clause type', clause)

    def addTermType(self, name, constructor):
        """
        Add a special kind of term type by name.
        """
        self._terms[name] = constructor

    def convertToSpecialTerm(self, term):
        """
        Convert a Term to a special Term known to this Brain.
        """
        if not term.args:
            return term
        first_arg = term.args[0]
        if isinstance(first_arg, Atom):
            constructor = self._terms.get(first_arg.value, None)
            if constructor is not None:
                return constructor(term)
        return term

    def query(self, query):
        """
        Query the brain.
        """
        log('query', query)
        query = PARSER(query).rule().normalizeVars().head
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
                    # trim it
                    for k in list(ret):
                        if not isinstance(k, Var):
                            ret.pop(k)
                    # merge in tags
                    ret.update(rule.head.tags)
                    log('   ret', ret)
                    yield ret
                else:
                    mapped_body = rule.body.substitute(mapping)
                    log('  MAKING', repr(mapped_body))
                    for match in mapped_body.query(self):
                        log(colored('\nQUERY {0!r}'.format(query), attrs=['dark']))
                        log(colored('  RULE  {0!r}'.format(rule), attrs=['dark']))
                        log(colored('  BODY  {0!r}'.format(mapped_body), attrs=['dark']))
                        log(colored('  mapping {0}'.format(mapping), attrs=['dark']))
                        log('  match  ', match)
                        rev_map = reverseDict(mapping)
                        log('  rev    ', rev_map)
                        
                        mapped_vars = [x for x in rev_map if isinstance(x, Var)]
                        ret = {}
                        for var in mapped_vars:
                            ret[var] = match.get(var, rev_map[var])
                        yield ret

