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
parens = '(' ws expression:e ws ')' -> e
value = atom | parens
add = '+' ws expr2:n -> ('+', n)
sub = '-' ws expr2:n -> ('-', n)
mul = '*' ws value:n -> ('*', n)
div = '/' ws value:n -> ('/', n)

addsub = ws (add | sub)
muldiv = ws (mul | div)

expression = expr2:left addsub*:right -> calculate(left, right)
expr2 = value:left muldiv*:right -> calculate(left, right)

#----------------------------
# tags
#----------------------------
tag_name = <tchar+>
tag = tag_name:key ws '=' ws atom:value -> (Atom(key), value)
tag_list = (tag:first (ws ',' ws tag)*:rest -> [first] + rest) | -> []
tagging = ws '@' ws tag_list:x -> dict(x)

tag_prop = <tchar+>:key ws '(' ws expression:val ws ')' -> (key, val)
tag_prop_list = (tag_prop:first (ws ',' ws tag_prop)*:rest -> [first] + rest) | -> []
tag_prop_def = '@' ws tag_name:name ws tag_prop_list:props -> TagProps(Atom(name), dict(props))

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

def _mergeWithoutOverwriting(a, b, tag_merge_rules=None):
    """
    Merge every new value in b into a
    """
    tag_merge_rules = tag_merge_rules or {}
    atags = a.pop('tags', {})
    btags = b.pop('tags', {})

    # merge normal data
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
    ret = a_copy

    # merge tags
    for tag,func in tag_merge_rules.items():
        ret['tags'] = tags = {}
        for k in set(atags) & set(btags):
            aval = atags.get(k, None)
            bval = btags.get(k, None)
            if aval is None:
                tags[k] = bval
            elif bval is None:
                tags[k] = aval
            else:
                tags[k] = func(aval, bval)
    return ret


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

    def pythonValue(self):
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
        self.tags = tags or {}

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

    def getTags(self, brain):
        tags = self.tags.copy()
        defaults = brain.defaultTags()
        for k in set(defaults) - set(tags):
            tags[k] = defaults[k]
        return tags

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

    def pythonValue(self):
        return tuple([x.pythonValue() for x in self.args])

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

    def pythonValue(self):
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
                        log('  match     ', match)
                        log('  tail_match', tail_match)
                        full_match = _mergeWithoutOverwriting(match, tail_match, brain.tagMergeRules())
                        log('  full_match', full_match)
                    except Conflict:
                        log('  conflict')
                        log('  match', match)
                        log('  tail ', tail_match)
                        continue
                    yield full_match
            else:
                log('no tail', match)
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


class BinaryOp(object):

    op = '?'

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return '[{0!r} {1} {2!r}]'.format(self.left, self.op, self.right)

    def evaluate(self, variables):
        left = self.left
        if isinstance(self.left, BinaryOp):
            left = left.evaluate(variables)
        else:
            left = left.pythonValue()
            left = variables.get(left, left)
        right = self.right
        if isinstance(self.right, BinaryOp):
            right = right.evaluate(variables)
        else:
            right = right.pythonValue()
            right = variables.get(right, right)
        return self._eval(left, right)


class Add(BinaryOp):
    op = '+'

    def _eval(self, left, right):
        print self, '_eval', left, right

class Sub(BinaryOp):
    op = '-'

    def _eval(self, left, right):
        print self, '_eval', left, right

class Mul(BinaryOp):
    op = '*'

    def _eval(self, left, right):
        print self, '_eval', left, right
        return left * right

class Div(BinaryOp):
    op = '/'

    def _eval(self, left, right):
        print self, '_eval', left, right


binops = {}
for cls in [Add, Sub, Mul, Div]:
    binops[cls.op] = cls

def calculate(start, pairs):
    result = start
    for op, right in pairs:
        result = binops[op](result, right)
    return result

grammar_bindings = {
    'Atom': Atom,
    'Term': Term,
    'Var': Var,
    'Rule': Rule,
    'And': And,
    'TRUE': TRUE,
    'Decimal': Decimal,
    'TagProps': TagProps,
    'calculate': calculate,
}
PARSER = parsley.makeGrammar(grammar, grammar_bindings)


def tobasicType(x):
    if hasattr(x, 'pythonValue'):
        return x.pythonValue()
    elif isinstance(x, dict):
        return humanizeDict(x)
    elif isinstance(x, (tuple, list)):
        return type(x)([tobasicType(z) for z in x])
    else:
        return x

def humanizeDict(d):
    return {tobasicType(k):tobasicType(v) for k,v in d.items()}


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

    def defaultTags(self):
        ret = {}
        for k,v in self.tag_props.items():
            print k, v
            if 'default' in v:
                ret[k] = v['default']
        return ret

    def tagMergeRules(self):
        """
        Get the merge rules for tags
        """
        ret = {}
        for k, v in self.tag_props.items():
            if 'and' in v:
                ret[k] = lambda x,y: v['and'].evaluate({
                    Atom('a'): x,
                    Atom('b'): y,
                    })
        return ret

    def query(self, query):
        """
        Query the brain.
        """
        log('query', query)
        query = PARSER(query).rule().normalizeVars().head
        log('parsed -> ', repr(query))
        for match in self.parsedQuery(query):
            log(colored('** {0}'.format(humanizeDict(match)), 'cyan'))
            ret = humanizeDict(match)
            yield ret

    def unique(self, gen):
        def flattenDicts(x):
            if isinstance(x, dict):
                return tuple(sorted((flattenDicts(k),flattenDicts(v)) for k,v in x.items()))
            else:
                return x
        encountered = set()
        for x in gen:
            h = hash(flattenDicts(x))
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
                    ret['tags'] = rule.head.getTags(brain=self)
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

