import unittest
import numpy as np
import itertools
import numpy.testing as np_test

from pgmpy.inference import VariableElimination
from pgmpy.inference import BeliefPropagation
from pgmpy.models import BayesianModel, MarkovModel
from pgmpy.models import JunctionTree
from pgmpy.factors.discrete import TabularCPD
from pgmpy.factors.discrete import DiscreteFactor


class TestVariableElimination(unittest.TestCase):
    def setUp(self):
        self.bayesian_model = BayesianModel(
            [("A", "J"), ("R", "J"), ("J", "Q"), ("J", "L"), ("G", "L")]
        )
        cpd_a = TabularCPD("A", 2, values=[[0.2], [0.8]])
        cpd_r = TabularCPD("R", 2, values=[[0.4], [0.6]])
        cpd_j = TabularCPD(
            "J",
            2,
            values=[[0.9, 0.6, 0.7, 0.1], [0.1, 0.4, 0.3, 0.9]],
            evidence=["A", "R"],
            evidence_card=[2, 2],
        )
        cpd_q = TabularCPD(
            "Q", 2, values=[[0.9, 0.2], [0.1, 0.8]], evidence=["J"], evidence_card=[2]
        )
        cpd_l = TabularCPD(
            "L",
            2,
            values=[[0.9, 0.45, 0.8, 0.1], [0.1, 0.55, 0.2, 0.9]],
            evidence=["J", "G"],
            evidence_card=[2, 2],
        )
        cpd_g = TabularCPD("G", 2, values=[[0.6], [0.4]])
        self.bayesian_model.add_cpds(cpd_a, cpd_g, cpd_j, cpd_l, cpd_q, cpd_r)

        self.bayesian_inference = VariableElimination(self.bayesian_model)

    # All the values that are used for comparision in the all the tests are
    # found using SAMIAM (assuming that it is correct ;))

    def test_query_single_variable(self):
        query_result = self.bayesian_inference.query(["J"])
        self.assertEqual(
            query_result,
            DiscreteFactor(variables=["J"], cardinality=[2], values=[0.416, 0.584]),
        )

    def test_query_multiple_variable(self):
        query_result = self.bayesian_inference.query(["Q", "J"])
        self.assertEqual(
            query_result,
            DiscreteFactor(
                variables=["J", "Q"],
                cardinality=[2, 2],
                values=np.array([[0.3744, 0.0416], [0.1168, 0.4672]]),
            ),
        )

    def test_query_single_variable_with_evidence(self):
        query_result = self.bayesian_inference.query(
            variables=["J"], evidence={"A": 0, "R": 1}
        )
        self.assertEqual(
            query_result,
            DiscreteFactor(variables=["J"], cardinality=[2], values=[0.6, 0.4]),
        )

    def test_query_multiple_variable_with_evidence(self):
        query_result = self.bayesian_inference.query(
            variables=["J", "Q"], evidence={"A": 0, "R": 0, "G": 0, "L": 1}
        )
        self.assertEqual(
            query_result,
            DiscreteFactor(
                variables=["J", "Q"],
                cardinality=[2, 2],
                values=np.array([[0.73636364, 0.08181818], [0.03636364, 0.14545455]]),
            ),
        )

    def test_query_multiple_times(self):
        # This just tests that the models are not getting modified while querying them
        query_result = self.bayesian_inference.query(["J"])
        query_result = self.bayesian_inference.query(["J"])
        self.assertEqual(
            query_result,
            DiscreteFactor(
                variables=["J"], cardinality=[2], values=np.array([0.416, 0.584])
            ),
        )
        query_result = self.bayesian_inference.query(["Q", "J"])
        query_result = self.bayesian_inference.query(["Q", "J"])
        self.assertEqual(
            query_result,
            DiscreteFactor(
                variables=["J", "Q"],
                cardinality=[2, 2],
                values=np.array([[0.3744, 0.0416], [0.1168, 0.4672]]),
            ),
        )

        query_result = self.bayesian_inference.query(
            variables=["J"], evidence={"A": 0, "R": 1}
        )
        query_result = self.bayesian_inference.query(
            variables=["J"], evidence={"A": 0, "R": 1}
        )
        self.assertEqual(
            query_result,
            DiscreteFactor(variables=["J"], cardinality=[2], values=[0.6, 0.4]),
        )

        query_result = self.bayesian_inference.query(
            variables=["J", "Q"], evidence={"A": 0, "R": 0, "G": 0, "L": 1}
        )
        query_result = self.bayesian_inference.query(
            variables=["J", "Q"], evidence={"A": 0, "R": 0, "G": 0, "L": 1}
        )
        self.assertEqual(
            query_result,
            DiscreteFactor(
                variables=["J", "Q"],
                cardinality=[2, 2],
                values=np.array([[0.73636364, 0.08181818], [0.03636364, 0.14545455]]),
            ),
        )

    def test_query_common_var(self):
        self.assertRaises(
            ValueError, self.bayesian_inference.query, variables=["J"], evidence=["J"]
        )

    def test_max_marginal(self):
        np_test.assert_almost_equal(
            self.bayesian_inference.max_marginal(), 0.1659, decimal=4
        )

    def test_max_marginal_var(self):
        np_test.assert_almost_equal(
            self.bayesian_inference.max_marginal(["G"]), 0.6, decimal=4
        )

    def test_max_marginal_var1(self):
        np_test.assert_almost_equal(
            self.bayesian_inference.max_marginal(["G", "R"]), 0.36, decimal=4
        )

    def test_max_marginal_var2(self):
        np_test.assert_almost_equal(
            self.bayesian_inference.max_marginal(["G", "R", "A"]), 0.288, decimal=4
        )

    def test_max_marginal_common_var(self):
        self.assertRaises(
            ValueError,
            self.bayesian_inference.max_marginal,
            variables=["J"],
            evidence=["J"],
        )

    def test_map_query(self):
        map_query = self.bayesian_inference.map_query()
        self.assertDictEqual(
            map_query, {"A": 1, "R": 1, "J": 1, "Q": 1, "G": 0, "L": 0}
        )

    def test_map_query_with_evidence(self):
        map_query = self.bayesian_inference.map_query(
            ["A", "R", "L"], {"J": 0, "Q": 1, "G": 0}
        )
        self.assertDictEqual(map_query, {"A": 1, "R": 0, "L": 0})

    def test_map_query_common_var(self):
        self.assertRaises(
            ValueError,
            self.bayesian_inference.map_query,
            variables=["J"],
            evidence=["J"],
        )

    def test_elimination_order(self):
        # Check all the heuristics give the same results.
        for elimination_order in [
            "WeightedMinFill",
            "MinNeighbors",
            "MinWeight",
            "MinFill",
        ]:
            query_result = self.bayesian_inference.query(
                ["J"], elimination_order=elimination_order
            )
            self.assertEqual(
                query_result,
                DiscreteFactor(variables=["J"], cardinality=[2], values=[0.416, 0.584]),
            )

            query_result = self.bayesian_inference.query(
                variables=["J"], evidence={"A": 0, "R": 1}
            )
            self.assertEqual(
                query_result,
                DiscreteFactor(variables=["J"], cardinality=[2], values=[0.6, 0.4]),
            )

        # Check when elimination order has extra variables. Because of pruning.
        query_result = self.bayesian_inference.query(
            ["J"], elimination_order=["A", "R", "L", "Q", "G"]
        )
        self.assertEqual(
            query_result,
            DiscreteFactor(variables=["J"], cardinality=[2], values=[0.416, 0.584]),
        )

        # Check for when elimination order doesn't have all the variables
        self.assertRaises(
            ValueError,
            self.bayesian_inference.query,
            variables=["J"],
            elimination_order=["A"],
        )

    def test_induced_graph(self):
        induced_graph = self.bayesian_inference.induced_graph(
            ["G", "Q", "A", "J", "L", "R"]
        )
        result_edges = sorted([sorted(x) for x in induced_graph.edges()])
        self.assertEqual(
            [
                ["A", "J"],
                ["A", "R"],
                ["G", "J"],
                ["G", "L"],
                ["J", "L"],
                ["J", "Q"],
                ["J", "R"],
                ["L", "R"],
            ],
            result_edges,
        )

    def test_induced_width(self):
        result_width = self.bayesian_inference.induced_width(
            ["G", "Q", "A", "J", "L", "R"]
        )
        self.assertEqual(2, result_width)

    def tearDown(self):
        del self.bayesian_inference
        del self.bayesian_model


class TestVariableEliminationDuplicatedFactors(unittest.TestCase):
    def setUp(self):
        self.markov_model = MarkovModel([("A", "B"), ("A", "C")])
        f1 = DiscreteFactor(
            variables=["A", "B"], cardinality=[2, 2], values=np.eye(2) * 2
        )
        f2 = DiscreteFactor(
            variables=["A", "C"], cardinality=[2, 2], values=np.eye(2) * 2
        )
        self.markov_model.add_factors(f1, f2)
        self.markov_inference = VariableElimination(self.markov_model)

    def test_duplicated_factors(self):
        query_result = self.markov_inference.query(["A"])
        self.assertEqual(
            query_result,
            DiscreteFactor(variables=["A"], cardinality=[2], values=np.array([4, 4])),
        )


class TestVariableEliminationMarkov(unittest.TestCase):
    def setUp(self):
        # It is just a moralised version of the above Bayesian network so all the results are same. Only factors
        # are under consideration for inference so this should be fine.
        self.markov_model = MarkovModel(
            [
                ("A", "J"),
                ("R", "J"),
                ("J", "Q"),
                ("J", "L"),
                ("G", "L"),
                ("A", "R"),
                ("J", "G"),
            ]
        )

        factor_a = TabularCPD("A", 2, values=[[0.2], [0.8]]).to_factor()
        factor_r = TabularCPD("R", 2, values=[[0.4], [0.6]]).to_factor()
        factor_j = TabularCPD(
            "J",
            2,
            values=[[0.9, 0.6, 0.7, 0.1], [0.1, 0.4, 0.3, 0.9]],
            evidence=["A", "R"],
            evidence_card=[2, 2],
        ).to_factor()
        factor_q = TabularCPD(
            "Q", 2, values=[[0.9, 0.2], [0.1, 0.8]], evidence=["J"], evidence_card=[2]
        ).to_factor()
        factor_l = TabularCPD(
            "L",
            2,
            values=[[0.9, 0.45, 0.8, 0.1], [0.1, 0.55, 0.2, 0.9]],
            evidence=["J", "G"],
            evidence_card=[2, 2],
        ).to_factor()
        factor_g = TabularCPD("G", 2, [[0.6], [0.4]]).to_factor()

        self.markov_model.add_factors(
            factor_a, factor_r, factor_j, factor_q, factor_l, factor_g
        )
        self.markov_inference = VariableElimination(self.markov_model)

    # All the values that are used for comparision in the all the tests are
    # found using SAMIAM (assuming that it is correct ;))

    def test_query_single_variable(self):
        query_result = self.markov_inference.query(["J"])
        self.assertEqual(
            query_result,
            DiscreteFactor(
                variables=["J"], cardinality=[2], values=np.array([0.416, 0.584])
            ),
        )

    def test_query_multiple_variable(self):
        query_result = self.markov_inference.query(["Q", "J"])
        self.assertEqual(
            query_result,
            DiscreteFactor(
                variables=["Q", "J"],
                cardinality=[2, 2],
                values=np.array([[0.3744, 0.1168], [0.0416, 0.4672]]),
            ),
        )

    def test_query_single_variable_with_evidence(self):
        query_result = self.markov_inference.query(
            variables=["J"], evidence={"A": 0, "R": 1}
        )
        self.assertEqual(
            query_result,
            DiscreteFactor(variables=["J"], cardinality=[2], values=[0.6, 0.4]),
        )

    def test_query_multiple_variable_with_evidence(self):
        query_result = self.markov_inference.query(
            variables=["J", "Q"], evidence={"A": 0, "R": 0, "G": 0, "L": 1}
        )
        self.assertEqual(
            query_result,
            DiscreteFactor(
                variables=["Q", "J"],
                cardinality=[2, 2],
                values=np.array([[0.081, 0.004], [0.009, 0.016]]),
            ),
        )

    def test_query_multiple_times(self):
        # This just tests that the models are not getting modified while querying them
        query_result = self.markov_inference.query(["J"])
        query_result = self.markov_inference.query(["J"])
        self.assertEqual(
            query_result,
            DiscreteFactor(
                variables=["J"], cardinality=[2], values=np.array([0.416, 0.584])
            ),
        )

        query_result = self.markov_inference.query(["Q", "J"])
        query_result = self.markov_inference.query(["Q", "J"])
        self.assertEqual(
            query_result,
            DiscreteFactor(
                variables=["Q", "J"],
                cardinality=[2, 2],
                values=np.array([[0.3744, 0.1168], [0.0416, 0.4672]]),
            ),
        )

        query_result = self.markov_inference.query(
            variables=["J"], evidence={"A": 0, "R": 1}
        )
        query_result = self.markov_inference.query(
            variables=["J"], evidence={"A": 0, "R": 1}
        )
        self.assertEqual(
            query_result,
            DiscreteFactor(variables=["J"], cardinality=[2], values=[0.6, 0.4]),
        )

        query_result = self.markov_inference.query(
            variables=["J", "Q"], evidence={"A": 0, "R": 0, "G": 0, "L": 1}
        )
        query_result = self.markov_inference.query(
            variables=["J", "Q"], evidence={"A": 0, "R": 0, "G": 0, "L": 1}
        )
        self.assertEqual(
            query_result,
            DiscreteFactor(
                variables=["Q", "J"],
                cardinality=[2, 2],
                values=np.array([[0.081, 0.004], [0.009, 0.016]]),
            ),
        )

    def test_max_marginal(self):
        np_test.assert_almost_equal(
            self.markov_inference.max_marginal(), 0.1659, decimal=4
        )

    def test_max_marginal_var(self):
        np_test.assert_almost_equal(
            self.markov_inference.max_marginal(["G"]), 0.1659, decimal=4
        )

    def test_max_marginal_var1(self):
        np_test.assert_almost_equal(
            self.markov_inference.max_marginal(["G", "R"]), 0.1659, decimal=4
        )

    def test_max_marginal_var2(self):
        np_test.assert_almost_equal(
            self.markov_inference.max_marginal(["G", "R", "A"]), 0.1659, decimal=4
        )

    def test_map_query(self):
        map_query = self.markov_inference.map_query()
        self.assertDictEqual(
            map_query, {"A": 1, "R": 1, "J": 1, "Q": 1, "G": 0, "L": 0}
        )

    def test_map_query_with_evidence(self):
        map_query = self.markov_inference.map_query(
            ["A", "R", "L"], {"J": 0, "Q": 1, "G": 0}
        )
        self.assertDictEqual(map_query, {"A": 1, "R": 0, "L": 0})

    def test_induced_graph(self):
        induced_graph = self.markov_inference.induced_graph(
            ["G", "Q", "A", "J", "L", "R"]
        )
        result_edges = sorted([sorted(x) for x in induced_graph.edges()])
        self.assertEqual(
            [
                ["A", "J"],
                ["A", "R"],
                ["G", "J"],
                ["G", "L"],
                ["J", "L"],
                ["J", "Q"],
                ["J", "R"],
                ["L", "R"],
            ],
            result_edges,
        )

    def test_induced_width(self):
        result_width = self.markov_inference.induced_width(
            ["G", "Q", "A", "J", "L", "R"]
        )
        self.assertEqual(2, result_width)

    def test_issue_1421(self):
        model = BayesianModel([("X", "Y"), ("Z", "X"), ("W", "Y")])
        cpd_z = TabularCPD(variable="Z", variable_card=2, values=[[0.5], [0.5]])

        cpd_x = TabularCPD(
            variable="X",
            variable_card=2,
            values=[[0.25, 0.75], [0.75, 0.25]],
            evidence=["Z"],
            evidence_card=[2],
        )

        cpd_w = TabularCPD(variable="W", variable_card=2, values=[[0.5], [0.5]])
        cpd_y = TabularCPD(
            variable="Y",
            variable_card=2,
            values=[[0.3, 0.4, 0.7, 0.8], [0.7, 0.6, 0.3, 0.2]],
            evidence=["X", "W"],
            evidence_card=[2, 2],
        )

        model.add_cpds(cpd_z, cpd_x, cpd_w, cpd_y)

        infer = VariableElimination(model)
        np_test.assert_array_almost_equal(
            infer.query(["Y"], evidence={"X": 0}).values, [0.35, 0.65]
        )

    def tearDown(self):
        del self.markov_inference
        del self.markov_model


class TestBeliefPropagation(unittest.TestCase):
    def setUp(self):
        self.junction_tree = JunctionTree(
            [(("A", "B"), ("B", "C")), (("B", "C"), ("C", "D"))]
        )
        phi1 = DiscreteFactor(["A", "B"], [2, 3], range(6))
        phi2 = DiscreteFactor(["B", "C"], [3, 2], range(6))
        phi3 = DiscreteFactor(["C", "D"], [2, 2], range(4))
        self.junction_tree.add_factors(phi1, phi2, phi3)

        self.bayesian_model = BayesianModel(
            [("A", "J"), ("R", "J"), ("J", "Q"), ("J", "L"), ("G", "L")]
        )
        cpd_a = TabularCPD("A", 2, values=[[0.2], [0.8]])
        cpd_r = TabularCPD("R", 2, values=[[0.4], [0.6]])
        cpd_j = TabularCPD(
            "J",
            2,
            values=[[0.9, 0.6, 0.7, 0.1], [0.1, 0.4, 0.3, 0.9]],
            evidence=["A", "R"],
            evidence_card=[2, 2],
        )
        cpd_q = TabularCPD(
            "Q", 2, values=[[0.9, 0.2], [0.1, 0.8]], evidence=["J"], evidence_card=[2]
        )
        cpd_l = TabularCPD(
            "L",
            2,
            values=[[0.9, 0.45, 0.8, 0.1], [0.1, 0.55, 0.2, 0.9]],
            evidence=["J", "G"],
            evidence_card=[2, 2],
        )
        cpd_g = TabularCPD("G", 2, values=[[0.6], [0.4]])
        self.bayesian_model.add_cpds(cpd_a, cpd_g, cpd_j, cpd_l, cpd_q, cpd_r)

    def test_calibrate_clique_belief(self):
        belief_propagation = BeliefPropagation(self.junction_tree)
        belief_propagation.calibrate()
        clique_belief = belief_propagation.get_clique_beliefs()

        phi1 = DiscreteFactor(["A", "B"], [2, 3], range(6))
        phi2 = DiscreteFactor(["B", "C"], [3, 2], range(6))
        phi3 = DiscreteFactor(["C", "D"], [2, 2], range(4))

        b_A_B = phi1 * (phi3.marginalize(["D"], inplace=False) * phi2).marginalize(
            ["C"], inplace=False
        )
        b_B_C = phi2 * (
            phi1.marginalize(["A"], inplace=False)
            * phi3.marginalize(["D"], inplace=False)
        )
        b_C_D = phi3 * (phi1.marginalize(["A"], inplace=False) * phi2).marginalize(
            ["B"], inplace=False
        )

        np_test.assert_array_almost_equal(
            clique_belief[("A", "B")].values, b_A_B.values
        )
        np_test.assert_array_almost_equal(
            clique_belief[("B", "C")].values, b_B_C.values
        )
        np_test.assert_array_almost_equal(
            clique_belief[("C", "D")].values, b_C_D.values
        )

    def test_calibrate_sepset_belief(self):
        belief_propagation = BeliefPropagation(self.junction_tree)
        belief_propagation.calibrate()
        sepset_belief = belief_propagation.get_sepset_beliefs()

        phi1 = DiscreteFactor(["A", "B"], [2, 3], range(6))
        phi2 = DiscreteFactor(["B", "C"], [3, 2], range(6))
        phi3 = DiscreteFactor(["C", "D"], [2, 2], range(4))

        b_B = (
            phi1
            * (phi3.marginalize(["D"], inplace=False) * phi2).marginalize(
                ["C"], inplace=False
            )
        ).marginalize(["A"], inplace=False)

        b_C = (
            phi2
            * (
                phi1.marginalize(["A"], inplace=False)
                * phi3.marginalize(["D"], inplace=False)
            )
        ).marginalize(["B"], inplace=False)

        np_test.assert_array_almost_equal(
            sepset_belief[frozenset((("A", "B"), ("B", "C")))].values, b_B.values
        )
        np_test.assert_array_almost_equal(
            sepset_belief[frozenset((("B", "C"), ("C", "D")))].values, b_C.values
        )

    def test_max_calibrate_clique_belief(self):
        belief_propagation = BeliefPropagation(self.junction_tree)
        belief_propagation.max_calibrate()
        clique_belief = belief_propagation.get_clique_beliefs()

        phi1 = DiscreteFactor(["A", "B"], [2, 3], range(6))
        phi2 = DiscreteFactor(["B", "C"], [3, 2], range(6))
        phi3 = DiscreteFactor(["C", "D"], [2, 2], range(4))

        b_A_B = phi1 * (phi3.maximize(["D"], inplace=False) * phi2).maximize(
            ["C"], inplace=False
        )
        b_B_C = phi2 * (
            phi1.maximize(["A"], inplace=False) * phi3.maximize(["D"], inplace=False)
        )
        b_C_D = phi3 * (phi1.maximize(["A"], inplace=False) * phi2).maximize(
            ["B"], inplace=False
        )

        np_test.assert_array_almost_equal(
            clique_belief[("A", "B")].values, b_A_B.values
        )
        np_test.assert_array_almost_equal(
            clique_belief[("B", "C")].values, b_B_C.values
        )
        np_test.assert_array_almost_equal(
            clique_belief[("C", "D")].values, b_C_D.values
        )

    def test_max_calibrate_sepset_belief(self):
        belief_propagation = BeliefPropagation(self.junction_tree)
        belief_propagation.max_calibrate()
        sepset_belief = belief_propagation.get_sepset_beliefs()

        phi1 = DiscreteFactor(["A", "B"], [2, 3], range(6))
        phi2 = DiscreteFactor(["B", "C"], [3, 2], range(6))
        phi3 = DiscreteFactor(["C", "D"], [2, 2], range(4))

        b_B = (
            phi1
            * (phi3.maximize(["D"], inplace=False) * phi2).maximize(
                ["C"], inplace=False
            )
        ).maximize(["A"], inplace=False)

        b_C = (
            phi2
            * (
                phi1.maximize(["A"], inplace=False)
                * phi3.maximize(["D"], inplace=False)
            )
        ).maximize(["B"], inplace=False)

        np_test.assert_array_almost_equal(
            sepset_belief[frozenset((("A", "B"), ("B", "C")))].values, b_B.values
        )
        np_test.assert_array_almost_equal(
            sepset_belief[frozenset((("B", "C"), ("C", "D")))].values, b_C.values
        )

    # All the values that are used for comparision in the all the tests are
    # found using SAMIAM (assuming that it is correct ;))

    def test_query_single_variable(self):
        belief_propagation = BeliefPropagation(self.bayesian_model)
        query_result = belief_propagation.query(["J"])
        self.assertEqual(
            query_result,
            DiscreteFactor(variables=["J"], cardinality=[2], values=[0.416, 0.584]),
        )

    def test_query_multiple_variable(self):
        belief_propagation = BeliefPropagation(self.bayesian_model)
        query_result = belief_propagation.query(["Q", "J"])
        self.assertEqual(
            query_result,
            DiscreteFactor(
                variables=["J", "Q"],
                cardinality=[2, 2],
                values=np.array([[0.3744, 0.0416], [0.1168, 0.4672]]),
            ),
        )

    def test_query_single_variable_with_evidence(self):
        belief_propagation = BeliefPropagation(self.bayesian_model)
        query_result = belief_propagation.query(
            variables=["J"], evidence={"A": 0, "R": 1}
        )
        self.assertEqual(
            query_result,
            DiscreteFactor(
                variables=["J"], cardinality=[2], values=np.array([0.6, 0.4])
            ),
        )

    def test_query_multiple_variable_with_evidence(self):
        belief_propagation = BeliefPropagation(self.bayesian_model)
        query_result = belief_propagation.query(
            variables=["J", "Q"], evidence={"A": 0, "R": 0, "G": 0, "L": 1}
        )
        self.assertEqual(
            query_result,
            DiscreteFactor(
                variables=["J", "Q"],
                cardinality=[2, 2],
                values=np.array([[0.73636364, 0.08181818], [0.03636364, 0.14545455]]),
            ),
        )

    def test_query_common_var(self):
        belief_propagation = BeliefPropagation(self.bayesian_model)
        self.assertRaises(
            ValueError, belief_propagation.query, variables=["J"], evidence=["J"]
        )

    def test_map_query(self):
        belief_propagation = BeliefPropagation(self.bayesian_model)
        map_query = belief_propagation.map_query()
        self.assertDictEqual(
            map_query, {"A": 1, "R": 1, "J": 1, "Q": 1, "G": 0, "L": 0}
        )

    def test_map_query_with_evidence(self):
        belief_propagation = BeliefPropagation(self.bayesian_model)
        map_query = belief_propagation.map_query(
            ["A", "R", "L"], {"J": 0, "Q": 1, "G": 0}
        )
        self.assertDictEqual(map_query, {"A": 1, "R": 0, "L": 0})

    def test_map_query_common_var(self):
        belief_propagation = BeliefPropagation(self.bayesian_model)
        self.assertRaises(
            ValueError, belief_propagation.map_query, variables=["J"], evidence=["J"]
        )

    def test_issue_1048(self):
        model = BayesianModel()

        # Nodes
        parents = ["parent"]
        children = [f"child_{i}" for i in range(10)]

        # Add nodes and edges
        model.add_nodes_from(parents + children)
        model.add_edges_from(itertools.product(parents, children))

        # Add cpds
        model.add_cpds(TabularCPD(parents[0], 2, [[0.5], [0.5]]))
        for c in children:
            model.add_cpds(
                TabularCPD(
                    c, 2, [[0.9, 0.1], [0.1, 0.9]], evidence=parents, evidence_card=[2]
                )
            )

        # Infer
        inf = BeliefPropagation(model)
        inf.calibrate()
        evidence = {}

        expected_evidences = [
            {},
            {"child_0": 1},
            {"child_0": 1, "child_1": 1},
            {"child_0": 1, "child_1": 1, "child_2": 1},
        ]
        expected_values = [
            np.array([0.5, 0.5]),
            np.array([0.1, 0.9]),
            np.array([0.0122, 0.9878]),
            np.array([0.0014, 0.9987]),
        ]
        for i, c in enumerate(children[:4]):
            self.assertEqual(evidence, expected_evidences[i])
            np_test.assert_almost_equal(
                inf.query(["parent"], evidence).normalize(inplace=False).values,
                expected_values[i],
                decimal=2,
            )
            evidence.update({c: 1})

    def tearDown(self):
        del self.junction_tree
        del self.bayesian_model
