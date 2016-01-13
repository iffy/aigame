from unittest import TestCase


from prolly import Brain, Var, Term


class BrainTest(TestCase):

    def test_basic_100percent(self):
        """
        A brain can store facts and be queried for stuff.
        """
        print ''
        brain = Brain()
        brain.addFact('mother_child', ['trudy', 'sally'])
        results = list(brain.query('mother_child', [Var('Mother'), Var('Child')]))
        print results
        self.assertEqual(len(results), 1, "Should list the one relationship")
        self.assertEqual(results[0]['Mother'], 'trudy')
        self.assertEqual(results[0]['Child'], 'sally')

    def test_trueness1(self):
        """
        Some "facts" are only partially true (according to the Brain).
        """
        brain = Brain()
        brain.addFact('good', ['apples'], trueness=0.5)
        results = list(brain.query('good', [Var('X')]))
        self.assertEqual(len(results), 1, "Should list the one good thing")
        self.assertEqual(results[0]['X'], 'apples')
        self.assertEqual(results[0]['_trueness'], 0.5)

