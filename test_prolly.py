from unittest import TestCase
from decimal import Decimal

from prolly import Brain, Var


def assertObjectSubsetIn(testcase, listing, obj):
    is_match = False
    for item in listing:
        matches = True
        try:
            for k,v in obj.items():
                if item[k] != v:
                    matches = False
                    break
        except KeyError:
            matches = False
        if matches:
            is_match = True
    if not is_match:
        testcase.fail('Expecting {0!r} to contain {1!r}'.format(listing, obj))


class BrainTest(TestCase):

    def setUp(self):
        Var.count = 0

    def test_matchterm(self):
        """
        Variables should match whole terms.
        """
        brain = Brain()
        rules = [
            '(X, good) if (john, said, X)',
            '(john, said, hello)',
            '(john, said, (cats, eat, food))',
        ]
        map(brain.add, rules)
        results = list(brain.query('(Z, good)'))
        assertObjectSubsetIn(self, results, {
            'Z': 'hello',
        })
        assertObjectSubsetIn(self, results, {
            'Z': ('cats', 'eat', 'food'),
        })
        self.assertEqual(len(results), 2)

    def test_matchterm_deep(self):
        """
        Variables should match whole terms at any depth.
        """
        brain = Brain()
        rules = [
            '(X, good) if (john, said, X)',
            '(X, rad) if (X, good)',
            '(john, said, hello)',
            '(john, said, (cats, drink, milk))',
        ]
        map(brain.add, rules)
        results = list(brain.query('(X, rad)'))
        assertObjectSubsetIn(self, results, {
            'X': 'hello',
        })
        assertObjectSubsetIn(self, results, {
            'X': ('cats', 'drink', 'milk'),
        })

    def test_integers(self):
        """
        You can use integers.
        """
        brain = Brain()
        brain.add('(age, 52)')
        results = list(brain.query('(age, X)'))
        assertObjectSubsetIn(self, results, {
            'X': 52,
        })

    def test_integer_negative(self):
        brain = Brain()
        brain.add('(age, -52)')
        results = list(brain.query('(age, X)'))
        assertObjectSubsetIn(self, results, {
            'X': -52,
        })

    def test_decimal(self):
        """
        You can use Decimals.
        """
        brain = Brain()
        brain.add('(age, 5.2)')
        results = list(brain.query('(age, X)'))
        assertObjectSubsetIn(self, results, {
            'X': Decimal('5.2'),
        })

    def test_decimal_negative(self):
        brain = Brain()
        brain.add('(age, -0.42)')
        results = list(brain.query('(age, X)'))
        assertObjectSubsetIn(self, results, {
            'X': Decimal('-0.42'),
        })

    def test_not(self):
        """
        You can use not to negate stuff.
        """
        brain = Brain()
        map(brain.add, [
            '(good, X) if (not, (bad, X))',
            '(bad, cats)',
        ])
        results = list(brain.query('(good, cats)'))
        self.assertEqual(len(results), 0,
            "Cats are not good.")

        results = list(brain.query('(good, muffins)'))
        self.assertEqual(len(results), 1,
            "Muffins are good: %r" % (results,))


class ScenarioBrainTest(TestCase):
    """
    Tests based on the same set of rules.
    """

    def setUp(self):
        Var.count = 0
        self.brain = Brain()
        rules = [
            # rules
            '(parent, P, C) if (mother, P, C)',
            '(parent, P, C) if (father, P, C)',
            '(daughter, P, C) if (parent, P, C) and (female, C)',
            '(son, P, C) if (parent, P, C) and (male, C)',
            '(grandparent, G, C) if (parent, G, P) and (parent, P, C)',
            '(sibling, X, Y) if (parent, P, X) and (parent, P, Y)',
            # data
            '(female, alicia)',
            '(mother, mary, alicia)',
            '(father, joseph, alicia)',
            '(mother, mary, mike)',
            '(father, joseph, mike)',
            '(mother, rita, joseph)',

        ]
        for r in rules:
            self.brain.add(r)

    def test_var_simple(self):
        """
        You can find out the answer to things using variables.
        """
        #for rule in self.brain._rules:
        #    print repr(rule)
        results = list(self.brain.query('(mother, X, alicia)'))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['X'], 'mary')

    def test_var_1level(self):
        results = list(self.brain.query('(parent, X, alicia)'))
        self.assertEqual(len(results), 2)
        assertObjectSubsetIn(self, results, {
            'X': 'mary',
        })
        assertObjectSubsetIn(self, results, {
            'X': 'joseph',
        })

    def test_var_sibling(self):
        results = list(self.brain.query('(sibling, X, alicia)'))
        self.assertEqual(len(results), 2, results)
        assertObjectSubsetIn(self, results, {
            'X': 'alicia',
        })
        assertObjectSubsetIn(self, results, {
            'X': 'mike',
        })

    def test_var_conjunction(self):
        """
        You can use conjunctions
        """
        results = list(self.brain.query('(daughter, mary, X)'))
        self.assertEqual(len(results), 1, results)
        assertObjectSubsetIn(self, results, {
            'X': 'alicia',
        })

    def test_var_multiple(self):
        """
        You can use multiple variables.
        """
        results = list(self.brain.query('(X, Y, mike)'))
        self.assertEqual(len(results), 7, results)
        assertObjectSubsetIn(self, results, {
            'X': 'father',
            'Y': 'joseph',
        })
        assertObjectSubsetIn(self, results, {
            'X': 'mother',
            'Y': 'mary',
        })
        assertObjectSubsetIn(self, results, {
            'X': 'grandparent',
            'Y': 'rita',
        })
        assertObjectSubsetIn(self, results, {
            'X': 'parent',
            'Y': 'joseph',
        })
        assertObjectSubsetIn(self, results, {
            'X': 'parent',
            'Y': 'mary',
        })
        assertObjectSubsetIn(self, results, {
            'X': 'sibling',
            'Y': 'alicia',
        })
        assertObjectSubsetIn(self, results, {
            'X': 'sibling',
            'Y': 'mike',
        })
