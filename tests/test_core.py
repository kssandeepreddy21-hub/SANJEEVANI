"""
tests/test_core.py
------------------
Automated unit & integration tests for the SANJEEVANI Six-Section Dashboard.
Verifies:
  1. Synthetic city data & NetworkX graph construction
  2. Road failure simulation & disconnected node handling
  3. Future Intelligence (T+0, T+15, T+30, T+60) projections
  4. Rescue Planning (Strategy A, B, C) & blocked road avoidance
  5. Benchmark evaluation across identical scenarios
  6. SHA-256 Hash-Chained Audit Log & tamper detection
"""

import unittest

from sanjeevani import audit, benchmark, data, decision, twin


class TestSanjeevaniCore(unittest.TestCase):
    def setUp(self):
        self.scenario = data.get_scenario_names()[1]  # Severe Urban Flood (65 mm/hr)
        self.incidents = data.get_synthetic_incidents(self.scenario)

    def test_networkx_graph_and_blocked_exclusion(self):
        g_all = data.build_city_road_graph(self.scenario, include_blocked=True)
        g_pass = data.build_city_road_graph(self.scenario, include_blocked=False)
        self.assertEqual(g_all.number_of_nodes(), 6)
        self.assertEqual(g_all.number_of_edges(), 8)
        self.assertLess(g_pass.number_of_edges(), g_all.number_of_edges())
        for _, _, edge_attrs in g_pass.edges(data=True):
            self.assertNotEqual(edge_attrs["status"], "BLOCKED")

    def test_road_failure_and_isolation_handling(self):
        res_base = data.evaluate_network_resilience(self.scenario)
        self.assertEqual(res_base["hospital_access_pct"], 100.0)

        res_iso = data.evaluate_network_resilience(
            self.scenario,
            manual_failed_roads={"RD-105", "RD-108"},
        )
        self.assertLess(res_iso["hospital_access_pct"], 100.0)
        self.assertEqual(res_iso["isolated_population"], 8400)

    def test_future_intelligence_projections(self):
        horizons_low = twin.simulate_all_horizons(self.scenario, rainfall_mm_hr=20)
        horizons_high = twin.simulate_all_horizons(self.scenario, rainfall_mm_hr=130)
        self.assertEqual(set(horizons_low.keys()), {0, 15, 30, 60})
        self.assertGreater(
            horizons_high[60]["blocked_count"],
            horizons_low[60]["blocked_count"],
        )

    def test_rescue_planning_strategies(self):
        comp_df = decision.compare_all_strategies(self.scenario, self.incidents)
        self.assertEqual(len(comp_df), 3)
        res_c = decision.allocate_rescue_resources(
            self.scenario,
            self.incidents,
            strategy_name="Strategy C – Risk-Aware Response (SANJEEVANI)",
        )
        self.assertGreater(res_c["assigned_count"], 0)
        self.assertEqual(res_c["unreachable_count"], 0)

    def test_benchmark_evaluation(self):
        bench = benchmark.run_benchmark_evaluation(
            self.scenario,
            self.incidents,
            response_threshold_min=8.0,
        )
        self.assertEqual(len(bench["summary_df"]), 3)
        self.assertEqual(bench["strategy_c"]["Blocked-Road Assignments"], 0)
        self.assertGreater(bench["strategy_a"]["Blocked-Road Assignments"], 0)

    def test_audit_sha256_hash_chain_and_tamper_detection(self):
        log = audit.create_initial_audit_log()
        self.assertEqual(len(log), 8)
        ok, _ = audit.verify_audit_chain(log)
        self.assertTrue(ok)

        # Tamper with entry #2
        log[1]["details"] = "TAMPERED PAYLOAD"
        ok_after, _ = audit.verify_audit_chain(log)
        self.assertFalse(ok_after)


if __name__ == "__main__":
    unittest.main()
