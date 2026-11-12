"""
tests/test_core.py
------------------
Automated unit, edge-case, and independent 6-section smoke tests for the
SANJEEVANI Six-Section Dashboard.
Verifies:
  - Core unit tests (1 - 6)
  - Expanded edge-case & module interface tests (7 - 15)
  - Independent Section Smoke Tests with timeout guards (16 - 21):
      * Section 1 – Overview
      * Section 2 – Resilience Lab
      * Section 3 – Live Response
      * Section 4 – Future Intelligence
      * Section 5 – Rescue Planning
      * Section 6 – Benchmark & Audit
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import time
import unittest
import folium
import pandas as pd

from sanjeevani import audit, benchmark, data, decision, evidence, resilience, twin


ALL_ROAD_IDS = {
    "RD-101",
    "RD-102",
    "RD-103",
    "RD-104",
    "RD-105",
    "RD-106",
    "RD-107",
    "RD-108",
}

SECTION_TIMEOUT_SEC = 5.0


def _run_with_timeout(fn, timeout_sec: float = SECTION_TIMEOUT_SEC):
    """Run a callable with a strict wall-clock timeout without using asyncio socketpair."""
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            result = future.result(timeout=timeout_sec)
        except FuturesTimeoutError as exc:
            raise AssertionError(
                f"Smoke test exceeded timeout of {timeout_sec}s"
            ) from exc
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return result, elapsed_ms


class TestSanjeevaniCore(unittest.TestCase):
    def setUp(self):
        self.scenario = data.get_scenario_names()[1]  # Severe Urban Flood (65 mm/hr)
        self.incidents = data.get_synthetic_incidents(self.scenario)

    # ------------------------------------------------------------------
    # EXISTING CORE TESTS (1 - 6)
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # EXPANDED EDGE-CASE & INTERFACE TESTS (7 - 15)
    # ------------------------------------------------------------------
    def test_total_network_isolation(self):
        """1. Total network isolation when all 8 roads are blocked."""
        res_total = data.evaluate_network_resilience(
            self.scenario,
            manual_failed_roads=ALL_ROAD_IDS,
        )
        self.assertFalse(res_total["is_fully_connected"])
        self.assertEqual(res_total["num_connected_components"], 6)
        self.assertGreater(res_total["isolated_population"], 0)
        self.assertLess(res_total["hospital_access_pct"], 100.0)

        g_pass = data.build_city_road_graph(
            self.scenario,
            manual_failed_roads=ALL_ROAD_IDS,
            include_blocked=False,
        )
        self.assertEqual(g_pass.number_of_edges(), 0)

    def test_empty_incident_tables(self):
        """2. Empty incident tables handled gracefully across decision and evidence modules."""
        empty_df = pd.DataFrame()
        res_empty = decision.allocate_rescue_resources(
            self.scenario,
            empty_df,
            strategy_name="Strategy C – Risk-Aware Response (SANJEEVANI)",
        )
        self.assertEqual(res_empty["assigned_count"], 0)
        self.assertEqual(res_empty["unreachable_count"], 0)
        self.assertEqual(res_empty["avg_response_eta_min"], 0.0)
        self.assertTrue(res_empty["allocations_df"].empty)

        comp_empty = decision.compare_all_strategies(self.scenario, empty_df)
        self.assertEqual(len(comp_empty), 3)
        self.assertTrue((comp_empty["Incidents Reached"] == 0).all())

        ev_summary = evidence.summarize_evidence_metrics(empty_df)
        self.assertEqual(ev_summary["total_reports"], 0)
        self.assertEqual(ev_summary["mean_confidence_pct"], 0.0)

    def test_upstream_audit_chain_breaks(self):
        """3. Upstream audit chain break propagation across subsequent entries."""
        log = audit.create_initial_audit_log()
        log[1]["details"] = "UNAUTHORIZED MODIFICATION"

        detailed = audit.verify_audit_chain_detailed(log)
        self.assertFalse(detailed["overall_valid"])
        self.assertEqual(detailed["status_label"], "INTEGRITY FAILURE")
        self.assertIn("AUD-002", detailed["failed_event_ids"])

        statuses = [e["Verification Status"] for e in detailed["entry_results"]]
        self.assertEqual(statuses[0], "✅ VERIFIED")
        self.assertEqual(statuses[1], "🚨 INTEGRITY FAILURE (Tampered Payload)")
        for downstream_status in statuses[2:]:
            self.assertEqual(downstream_status, "❌ CHAIN BROKEN (Upstream Hash Mismatch)")

    def test_resilience_module_interfaces(self):
        """4. Resilience module (sanjeevani/resilience.py) interfaces."""
        bundle = resilience.assess_road_network_resilience(self.scenario)
        self.assertEqual(bundle["total_nodes"], 6)
        self.assertEqual(bundle["total_roads"], 8)
        self.assertEqual(
            bundle["passable_edges"] + bundle["blocked_edges"],
            bundle["total_roads"],
        )
        self.assertEqual(len(bundle["critical_rankings_df"]), 8)

        stress = resilience.simulate_single_road_failure(
            self.scenario,
            road_id="RD-105",
            existing_failed_roads={"RD-108"},
        )
        self.assertIn("RD-105", stress["updated_failed_roads"])
        self.assertGreater(stress["access_drop_pct"], 0.0)
        self.assertEqual(stress["isolated_population"], 8400)

    def test_evidence_module_interfaces(self):
        """5. Evidence module (sanjeevani/evidence.py) interfaces & XSS sanitization."""
        scored = evidence.score_emergency_report(
            title="<script>alert('xss')</script> Flooded Clinic",
            sector="Sector 4 Lowlands",
            disaster_type="Medical Evacuation",
            urgency="CRITICAL",
            simulate_duplicate=False,
            existing_custom_count=0,
        )
        self.assertNotIn("<script>", scored["title"])
        self.assertIn("&lt;script&gt;", scored["title"])
        self.assertTrue(scored["verified"])
        self.assertGreaterEqual(scored["confidence"], 0.90)

        dup_scored = evidence.score_emergency_report(
            title="Recycled Flood Image",
            sector="East Basin",
            disaster_type="Flash Flood Entrapment",
            urgency="WARNING",
            simulate_duplicate=True,
            existing_custom_count=1,
        )
        self.assertFalse(dup_scored["verified"])
        self.assertIn("FLAGGED", dup_scored["duplicate_warning"])

        with self.assertRaises(ValueError):
            evidence.score_emergency_report(
                title="   ",
                sector="East Basin",
                disaster_type="Road Obstruction",
                urgency="WARNING",
            )

        filtered_crit = evidence.filter_incident_reports(
            self.incidents,
            urgency_filter="CRITICAL",
            verify_filter="Verified Only",
        )
        self.assertTrue((filtered_crit["urgency"] == "CRITICAL").all())
        self.assertTrue(filtered_crit["verified"].all())

    def test_blocked_road_handling(self):
        """6. Blocked roads are strictly excluded from routing and horizon graphs."""
        custom_failed = {"RD-102", "RD-106"}
        G_route, _ = decision.build_routing_graph(
            self.scenario,
            manual_failed_roads=custom_failed,
        )
        active_road_ids = {
            attrs["road_id"] for _, _, attrs in G_route.edges(data=True)
        }
        self.assertNotIn("RD-101", active_road_ids)
        self.assertNotIn("RD-103", active_road_ids)
        self.assertNotIn("RD-102", active_road_ids)
        self.assertNotIn("RD-106", active_road_ids)

    def test_unreachable_rescue_destinations(self):
        """7. Unreachable rescue destinations when all connecting roads to a sector fail."""
        res = decision.allocate_rescue_resources(
            self.scenario,
            self.incidents,
            strategy_name="Strategy C – Risk-Aware Response (SANJEEVANI)",
            manual_failed_roads={"RD-105", "RD-108"},
        )
        self.assertGreaterEqual(res["unreachable_count"], 1)
        df_alloc = res["allocations_df"]
        inc_901_row = df_alloc[df_alloc["Incident ID"] == "INC-901"].iloc[0]
        self.assertIn("UNREACHABLE", inc_901_row["Route Status"])

    def test_empty_resource_availability(self):
        """8. Empty rescue resource availability handled without runtime error."""
        empty_units = pd.DataFrame(
            columns=["unit_id", "type", "status", "assigned_sector", "lat", "lon"]
        )
        res = decision.allocate_rescue_resources(
            self.scenario,
            self.incidents,
            strategy_name="Strategy B – Fastest Response",
            units_df_override=empty_units,
        )
        self.assertEqual(res["assigned_count"], 0)
        self.assertEqual(res["unreachable_count"], len(self.incidents))
        self.assertEqual(res["unit_utilization_pct"], 0.0)

    def test_benchmark_edge_cases(self):
        """9. Benchmark edge cases (empty incidents, empty units, total isolation, sensitivity curve parity)."""
        empty_inc = pd.DataFrame()
        bench_empty = benchmark.run_benchmark_evaluation(
            self.scenario,
            empty_inc,
            response_threshold_min=8.0,
        )
        self.assertEqual(bench_empty["total_incidents"], 0)
        self.assertEqual(len(bench_empty["summary_df"]), 3)
        self.assertEqual(bench_empty["strategy_c"]["Reached Incidents"], 0)

        bench_isolated = benchmark.run_benchmark_evaluation(
            self.scenario,
            self.incidents,
            manual_failed_roads=ALL_ROAD_IDS,
            response_threshold_min=5.0,
        )
        self.assertEqual(len(bench_isolated["summary_df"]), 3)

        curve = twin.compute_rainfall_sensitivity_curve(
            self.scenario,
            manual_failed_roads={"RD-105"},
            rain_samples=[0, 75, 150],
        )
        for idx, rain_val in enumerate([0, 75, 150]):
            expected_h60 = twin.simulate_all_horizons(
                self.scenario,
                rainfall_mm_hr=float(rain_val),
                manual_failed_roads={"RD-105"},
            )[60]
            self.assertEqual(
                curve["access_curve"][idx],
                expected_h60["hospital_access_pct"],
            )

    # ------------------------------------------------------------------
    # INDEPENDENT SIX-SECTION SMOKE TESTS WITH TIMEOUTS (16 - 21)
    # ------------------------------------------------------------------
    def test_smoke_section_1_overview(self):
        """Smoke Test Section 1 (Overview): KPI calculations, alerts, Folium map, live audit stream."""
        def _check():
            metrics = data.get_overview_metrics(
                self.scenario,
                manual_failed_roads={"RD-105"},
                extra_incidents_count=1,
                extra_critical_count=1,
            )
            self.assertEqual(metrics["status_level"], "HIGH ALERT")
            self.assertEqual(metrics["total_incidents"], 15)
            self.assertEqual(metrics["critical_incidents"], 6)
            self.assertGreaterEqual(metrics["blocked_roads"], 3)

            alerts = data.get_critical_alerts(self.scenario)
            self.assertGreaterEqual(len(alerts), 4)
            self.assertTrue(all("severity" in a and "title" in a for a in alerts))

            # Folium map generation check
            roads = data.get_synthetic_roads(self.scenario)
            hospitals = data.get_synthetic_hospitals()
            teams = data.get_synthetic_rescue_teams()
            m = folium.Map(location=data.CITY_CENTER, zoom_start=13, tiles="CartoDB dark_matter")
            for r in roads:
                folium.PolyLine(locations=r["coords"]).add_to(m)
            self.assertEqual(len(hospitals), 3)
            self.assertEqual(len(teams), 4)
            rendered_html = m.get_root().render()
            self.assertIn("leaflet", rendered_html.lower())

            # Live audit stream & recent activity fallback
            log = audit.create_initial_audit_log()
            df_stream = audit.get_audit_dataframe(log)[
                ["Timestamp", "Stage", "Action", "Details"]
            ].head(8)
            self.assertEqual(len(df_stream), 8)
            df_fallback = data.get_recent_activity()
            self.assertFalse(df_fallback.empty)
            return True

        ok, elapsed_ms = _run_with_timeout(_check)
        self.assertTrue(ok)
        self.assertLess(elapsed_ms, SECTION_TIMEOUT_SEC * 1000.0)

    def test_smoke_section_2_resilience_lab(self):
        """Smoke Test Section 2 (Resilience Lab): NetworkX graph, road failure simulation, resilience, hospital reachability."""
        def _check():
            bundle = resilience.assess_road_network_resilience(self.scenario)
            self.assertEqual(bundle["total_nodes"], 6)
            self.assertEqual(bundle["total_roads"], 8)
            self.assertEqual(bundle["passable_edges"], 6)
            self.assertEqual(bundle["blocked_edges"], 2)
            self.assertEqual(bundle["resilience_eval"]["hospital_access_pct"], 100.0)

            # Simulate road failure on RD-105 & RD-108
            step1 = resilience.simulate_single_road_failure(
                self.scenario,
                road_id="RD-105",
            )
            step2 = resilience.simulate_single_road_failure(
                self.scenario,
                road_id="RD-108",
                existing_failed_roads=step1["updated_failed_roads"],
            )
            self.assertLess(step2["post_failure_access_pct"], 100.0)
            self.assertEqual(step2["isolated_population"], 8400)
            self.assertFalse(step2["is_fully_connected"])
            self.assertGreaterEqual(step2["num_connected_components"], 2)
            return True

        ok, elapsed_ms = _run_with_timeout(_check)
        self.assertTrue(ok)
        self.assertLess(elapsed_ms, SECTION_TIMEOUT_SEC * 1000.0)

    def test_smoke_section_3_live_response(self):
        """Smoke Test Section 3 (Live Response): Incident submission, verification, duplicate detection, road availability."""
        def _check():
            base_df = self.incidents.copy()
            # 1. Incident submission (unique + duplicate)
            new_unique = evidence.score_emergency_report(
                title="Trapped Commuters Near Underpass",
                sector="Sector 4 Lowlands",
                disaster_type="Flash Flood Entrapment",
                urgency="CRITICAL",
                simulate_duplicate=False,
                existing_custom_count=0,
            )
            new_dup = evidence.score_emergency_report(
                title="Recycled Social Media Flood Image",
                sector="East Basin",
                disaster_type="Flash Flood Entrapment",
                urgency="WARNING",
                simulate_duplicate=True,
                existing_custom_count=1,
            )
            self.assertTrue(new_unique["verified"])
            self.assertFalse(new_dup["verified"])
            self.assertIn("FLAGGED", new_dup["duplicate_warning"])

            combined_df = pd.concat(
                [pd.DataFrame([new_dup, new_unique]), base_df],
                ignore_index=True,
            )
            metrics = evidence.summarize_evidence_metrics(combined_df)
            self.assertEqual(metrics["total_reports"], 7)
            self.assertGreaterEqual(metrics["duplicate_flagged_count"], 2)

            # 2. Manual verification update
            combined_df.loc[
                combined_df["incident_id"] == new_dup["incident_id"], "verified"
            ] = True
            verified_only = evidence.filter_incident_reports(
                combined_df,
                verify_filter="Verified Only",
            )
            self.assertIn(
                new_dup["incident_id"],
                verified_only["incident_id"].tolist(),
            )

            # 3. Road availability updates & precautions
            roads_updated = data.get_synthetic_roads(
                self.scenario,
                manual_failed_roads={"RD-104"},
            )
            rd104 = next(r for r in roads_updated if r["road_id"] == "RD-104")
            self.assertEqual(rd104["status"], "BLOCKED")
            prec = data.get_precautions_by_disaster_type()
            self.assertGreaterEqual(len(prec), 4)
            return True

        ok, elapsed_ms = _run_with_timeout(_check)
        self.assertTrue(ok)
        self.assertLess(elapsed_ms, SECTION_TIMEOUT_SEC * 1000.0)

    def test_smoke_section_4_future_intelligence(self):
        """Smoke Test Section 4 (Future Intelligence): Rainfall sensitivity, risk estimation, T+0..T+60 projections, comparisons."""
        def _check():
            horizons = twin.simulate_all_horizons(
                self.scenario,
                rainfall_mm_hr=95.0,
                manual_failed_roads={"RD-105"},
            )
            self.assertEqual(set(horizons.keys()), {0, 15, 30, 60})
            self.assertGreaterEqual(
                horizons[60]["blocked_count"],
                horizons[0]["blocked_count"],
            )

            df_comp = twin.build_horizon_comparison_df(horizons)
            df_prog = twin.build_road_progression_df(horizons)
            casc = twin.get_cascading_impacts_and_observations(horizons)
            self.assertEqual(len(df_comp), 4)
            self.assertEqual(len(df_prog), 8)
            self.assertFalse(casc["cascading_df"].empty)
            self.assertFalse(casc["observations_df"].empty)

            curve = twin.compute_rainfall_sensitivity_curve(
                self.scenario,
                manual_failed_roads={"RD-105"},
            )
            self.assertEqual(len(curve["rain_samples"]), 7)
            self.assertEqual(len(curve["access_curve"]), 7)
            self.assertEqual(len(curve["blocked_pct_curve"]), 7)
            return True

        ok, elapsed_ms = _run_with_timeout(_check)
        self.assertTrue(ok)
        self.assertLess(elapsed_ms, SECTION_TIMEOUT_SEC * 1000.0)

    def test_smoke_section_5_rescue_planning(self):
        """Smoke Test Section 5 (Rescue Planning): Ambulance allocation, rescue routing, alternative routes, unreachable detection."""
        def _check():
            # Baseline allocation
            plan_base = decision.allocate_rescue_resources(
                self.scenario,
                self.incidents,
                strategy_name="Strategy C – Risk-Aware Response (SANJEEVANI)",
            )
            self.assertEqual(plan_base["assigned_count"], 4)
            self.assertEqual(plan_base["unreachable_count"], 0)
            self.assertEqual(len(plan_base["map_routes"]), 4)

            # Alternative route generation when RD-105 fails (J4 still reachable via RD-108)
            plan_alt = decision.allocate_rescue_resources(
                self.scenario,
                self.incidents,
                strategy_name="Strategy C – Risk-Aware Response (SANJEEVANI)",
                manual_failed_roads={"RD-105"},
            )
            self.assertEqual(plan_alt["unreachable_count"], 0)
            for rt in plan_alt["map_routes"]:
                self.assertNotIn("RD-105", rt["leg1_roads"])
                self.assertNotIn("RD-105", rt["leg2_roads"])

            # Unreachable incident detection when both RD-105 and RD-108 fail
            plan_unreach = decision.allocate_rescue_resources(
                self.scenario,
                self.incidents,
                strategy_name="Strategy C – Risk-Aware Response (SANJEEVANI)",
                manual_failed_roads={"RD-105", "RD-108"},
            )
            self.assertGreaterEqual(plan_unreach["unreachable_count"], 1)

            df_strat_comp = decision.compare_all_strategies(
                self.scenario,
                self.incidents,
            )
            self.assertEqual(len(df_strat_comp), 3)
            return True

        ok, elapsed_ms = _run_with_timeout(_check)
        self.assertTrue(ok)
        self.assertLess(elapsed_ms, SECTION_TIMEOUT_SEC * 1000.0)

    def test_smoke_section_6_benchmark_and_audit(self):
        """Smoke Test Section 6 (Benchmark & Audit): Strategy comparison, performance metrics, SHA-256 chain & verification."""
        def _check():
            bench = benchmark.run_benchmark_evaluation(
                self.scenario,
                self.incidents,
                manual_failed_roads={"RD-105"},
                response_threshold_min=8.0,
            )
            df_sum = bench["summary_df"]
            self.assertEqual(len(df_sum), 3)
            self.assertEqual(bench["strategy_c"]["Blocked-Road Assignments"], 0)
            self.assertEqual(bench["strategy_c"]["Unverified Duplicate Dispatches"], 0)
            self.assertGreaterEqual(
                bench["strategy_c"]["Hospital Accessibility (%)"],
                bench["strategy_a"]["Hospital Accessibility (%)"],
            )

            # SHA-256 Audit Chain Integrity & Verification
            log = audit.create_initial_audit_log()
            audit.append_audit_event(
                log,
                stage="VERIFY",
                action_type="Section 6 Smoke Test",
                details="Verified benchmark and audit integrity.",
            )
            self.assertEqual(len(log), 9)
            check_ok = audit.verify_audit_chain_detailed(log)
            self.assertTrue(check_ok["overall_valid"])
            self.assertEqual(check_ok["status_label"], "VERIFIED")

            # Tamper detection check
            log[1]["details"] = "TAMPERED_ENTRY"
            check_bad = audit.verify_audit_chain_detailed(log)
            self.assertFalse(check_bad["overall_valid"])
            self.assertEqual(check_bad["status_label"], "INTEGRITY FAILURE")
            return True

        ok, elapsed_ms = _run_with_timeout(_check)
        self.assertTrue(ok)
        self.assertLess(elapsed_ms, SECTION_TIMEOUT_SEC * 1000.0)


if __name__ == "__main__":
    unittest.main()
