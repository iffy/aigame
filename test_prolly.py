from unittest import TestCase


from prolly import Brain


def assertObjectSubsetIn(testcase, listing, obj):
    for x in listing:
        matches = True
        for k,v in obj.items():
            if x[k] != v:
                matches = False
                break
        if matches:
            return
    testcase.fail('Expecting {0!r} to contain {1!r}'.format(listing, obj))


class SimpleBrainTest(TestCase):

    def setUp(self):
        self.brain = Brain()
        rules = [
            # rules
            '(parent, P, C) if (mother, P, C)',
            '(parent, P, C) if (father, P, C)',
            '(grandparent, G, C) if (parent, G, P) and (parent, P, C)',
            '(sibling, X, Y) if (parent, P, X) and (parent, P, Y)',
            # data
            '(mother, mary, alicia)',
            '(father, joseph, alicia)',
            '(mother, mary, mike)',
            '(father, joseph, mike)',
            '(mother, rita, joseph)',

        ]
        for r in rules:
            self.brain.add(r)

    def test_truth_simple(self):
        results = list(self.brain.query('(mother, mary, alicia)'))
        self.assertEqual(len(results), 1)

    def test_truth_conjunction(self):
        results = list(self.brain.query('(sibling, mike, alicia)'))
        self.assertEqual(len(results), 1)

    def test_truth_false(self):
        results = list(self.brain.query('(mother, mary, gonzo)'))
        self.assertEqual(len(results), 0)

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
        self.assertEqual(len(results), 2)
        assertObjectSubsetIn(self, results, {
            'X': 'alicia',
        })
        assertObjectSubsetIn(self, results, {
            'X': 'mike',
        })

    def test_var_multiple(self):
        """
        You can use multiple variables.
        """
        results = list(self.brain.query('(X, Y, alicia)'))
        self.assertEqual(len(results), 2)
        assertObjectSubsetIn(self, results, {
            'X': 'father',
            'Y': 'joseph',
        })
        assertObjectSubsetIn(self, results, {
            'X': 'mother',
            'Y': 'mary',
        })
