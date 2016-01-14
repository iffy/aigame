from unittest import TestCase


from prolly import Brain, Var, Term, log, Rule, Conjunction


class BrainTest(TestCase):

    def test_basic_100percent(self):
        """
        A brain can store facts and be queried for stuff.
        """
        print ''
        brain = Brain()
        brain.addFact('mother_child', ['trudy', 'sally'])
        results = list(brain.pyquery('mother_child', [Var('Mother'), Var('Child')]))
        log('results', results)
        self.assertEqual(len(results), 1, "Should list the one relationship")
        self.assertEqual(results[0]['Mother'], 'trudy')
        self.assertEqual(results[0]['Child'], 'sally')

    def test_complex1(self):
        """
        A brain can store facts and be queried for related stuff.
        """
        print ''
        brain = Brain()
        # brain.addFact('father_child', ['massimo', 'ridge'])
        # brain.addFact('father_child', ['eric', 'thorne'])
        # brain.addFact('father_child', ['thorne', 'alexandria'])

        #brain.addFact('mother_child', ['stephanie', 'thorne'])
        brain.addFact('mother_child', ['mommy', 'paco'])
        brain.addFact('mother_child', ['mommy', 'jenny'])

        # brain.addRule(Rule(
        #     Term('parent_child', [Var('X'), Var('Y')]),
        #     Term('father_child', [Var('X'), Var('Y')])
        # ))

        brain.addRule(Rule(
            Term('parent_child', [Var('X'), Var('Y')]),
            Term('mother_child', [Var('X'), Var('Y')])
        ))

        brain.addRule(Rule(
            Term('sibling', [Var('X'), Var('Y')]),
            Conjunction([
                Term('parent_child', [Var('Z'), Var('X')]),
                Term('parent_child', [Var('Z'), Var('Y')]),
            ])
        ))

        # brain.addRule(Rule(
        #     Term('ancestor', [Var('X'), Var('Y')]),
        #     Term('parent_child', [Var('X'), Var('Y')]),
        # ))
        # brain.addRule(Rule(
        #     Term('ancestor', [Var('X'), Var('Y')]),
        #     Conjunction([
        #         Term('parent_child', [Var('X'), Var('Z')]),
        #         Term('ancestor', [Var('Z'), Var('Y')]),
        #     ])
        # ))

        results = list(brain.pyquery('parent_child', [Term('mommy'), Var('Child')]))
        log('results', results)
        self.assertEqual(len(results), 2, "She has two kids")
        self.assertEqual(results[0]['Child'], 'paco')
        self.assertEqual(results[1]['Child'], 'jenny')

        print ' '
        # results = list(brain.pyquery('sibling', [Var('Sibling'), Term('paco')]))
        # log('results', results)
        # self.assertEqual(len(results), 2, "She has 2 siblings")

