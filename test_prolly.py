from unittest import TestCase


from prolly import Brain


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


class SimpleBrainTest(TestCase):

    def setUp(self):
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
        self.assertEqual(len(results), 1)
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
