#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_consumer_answer.py"
FIXTURE = ROOT / "tests" / "fixtures" / "consumer-answer.json"
QUICK_FIXTURE = ROOT / "tests" / "fixtures" / "consumer-answer-quick.json"
CACHED_FIXTURE = ROOT / "tests" / "fixtures" / "vitamin-d-cached-answer.json"
MANIFEST = ROOT / "examples" / "neuriva-pubmed-search-manifest.json"
RIS = ROOT / "examples" / "neuriva-pubmed-search.ris"
SCREENING = ROOT / "examples" / "neuriva-pubmed-screening.csv"
FISH_FIXTURE = ROOT / "examples" / "cases" / "fish-oil" / "answer.json"
FISH_MANIFEST = ROOT / "examples" / "cases" / "fish-oil" / "pubmed-search-manifest.json"
FISH_RIS = ROOT / "examples" / "cases" / "fish-oil" / "pubmed-search.ris"
FISH_SCREENING = ROOT / "examples" / "cases" / "fish-oil" / "screening.csv"


class ConsumerAnswerTests(unittest.TestCase):
    def run_builder(self, payload, with_svg=False, manifest=MANIFEST, ris=RIS, screening=SCREENING, include_bundle=True, evidence_pack=None, intake_seconds_ago=None):
        temp = tempfile.TemporaryDirectory(prefix="consumer-answer-")
        base = Path(temp.name)
        source = base / "input.json"
        source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        command = [
            sys.executable,
            str(SCRIPT),
            str(source),
            "--html", str(base / "answer.html"),
        ]
        if include_bundle:
            command += [
                "--pubmed-manifest", str(manifest),
                "--pubmed-ris", str(ris),
                "--screening-log", str(screening),
            ]
        if evidence_pack:
            command += ["--evidence-pack", str(evidence_pack)]
        if intake_seconds_ago is not None:
            submitted_at = datetime.now(timezone.utc) - timedelta(seconds=intake_seconds_ago)
            intake = base / "intake-response.json"
            intake.write_text(
                json.dumps(
                    {
                        "submitted_at_utc": submitted_at.isoformat(timespec="seconds"),
                        "quick_result_deadline_utc": (submitted_at + timedelta(seconds=180)).isoformat(timespec="seconds"),
                    }
                ),
                encoding="utf-8",
            )
            command += ["--intake-response", str(intake)]
        if with_svg:
            command += ["--svg", str(base / "answer.svg")]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        return temp, base, result

    def test_builds_three_layer_html_and_optional_image(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        temp, base, result = self.run_builder(payload, with_svg=True)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertLessEqual(report["first_screen_chars"], 150)
        self.assertTrue(report["evidence_bundle_verified"])
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertEqual(page.count("<summary>"), 8)
        for marker in ('data-testid="why"', 'data-testid="suitability"', 'data-testid="research"'):
            self.assertIn(marker, page)
        self.assertIn("不太值得买。", page)
        self.assertIn("color:var(--color-danger)", page)
        self.assertNotIn("var(--#", page)
        self.assertIn("PICOS 与随访", page)
        self.assertIn("证据怎么裁决", page)
        self.assertIn("来源为何看似矛盾", page)
        self.assertIn("按关键结局综合判断", page)
        self.assertIn("与研究人群的匹配度", page)
        self.assertIn("基于快速证据综合的 GRADE 评级", page)
        self.assertIn("范围与流程简化", page)
        self.assertIn("可复现的 PubMed 检索", page)
        self.assertIn("完整检索式", page)
        self.assertIn("PubMed Query Translation", page)
        self.assertIn("筛选流程", page)
        self.assertIn("PICOS 纳入与排除", page)
        self.assertIn('aria-label="证据护照"', page)
        self.assertIn("检索覆盖", page)
        self.assertIn("GRADE 五域与理由", page)
        svg = (base / "answer.svg").read_text(encoding="utf-8")
        self.assertIn('width="1080" height="1350"', svg)
        self.assertIn("安全红线", svg)

    def test_builds_quick_card_without_pubmed_bundle_and_marks_boundary(self):
        payload = json.loads(QUICK_FIXTURE.read_text(encoding="utf-8"))
        temp, base, result = self.run_builder(payload, include_bundle=False)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["evidence_bundle_verified"])
        self.assertEqual(report["card_state"], "audit_updating")
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn("快速核验完成，完整审计更新中", page)
        self.assertIn("不是系统综述或正式 GRADE", page)
        self.assertIn("本地指南、DRIs 或监管标准", page)
        self.assertNotIn("可复现的 PubMed 检索", page)
        self.assertIn("只对特定人群值得。", page)
        self.assertIn('data-testid="next-actions"', page)
        self.assertIn('data-testid="continue-inquiry"', page)
        self.assertIn('data-testid="request-full-audit"', page)
        self.assertIn("完整审计更新中", page)
        self.assertIn("不会在后台自动运行", page)

    def test_completed_quick_card_offers_copyable_full_audit_request(self):
        payload = json.loads(QUICK_FIXTURE.read_text(encoding="utf-8"))
        payload["card_state"] = "quick_complete"
        payload["status_detail"] = "快速核验已完成；完整审计仅按用户要求进行。"
        temp, base, result = self.run_builder(payload, include_bundle=False)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn('data-testid="request-full-audit"', page)
        self.assertIn('data-copy-request="请把《', page)
        self.assertIn("升级为 L1-Audited 完整审计", page)
        self.assertIn("回到聊天粘贴并发送即可继续", page)

    def test_action_requests_escape_user_controlled_copy(self):
        payload = json.loads(QUICK_FIXTURE.read_text(encoding="utf-8"))
        payload["card_state"] = "quick_complete"
        payload["title"] = "<img src=x onerror=alert(1)>"
        payload["suitability"]["may_fit"] = ['\" onmouseover=\"alert(1)']
        temp, base, result = self.run_builder(payload, include_bundle=False)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertNotIn("<img src=x", page)
        self.assertNotIn('onmouseover="alert(1)', page)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", page)

    def test_personalized_conditional_verdict_confirms_a_known_match(self):
        payload = json.loads(QUICK_FIXTURE.read_text(encoding="utf-8"))
        payload["personal_match"] = "matched"
        payload["personalized_verdict"] = "可以补充，但每天一粒通常就够了。"
        temp, base, result = self.run_builder(payload, include_bundle=False)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["personal_match"], "matched")
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn("可以补充，但每天一粒通常就够了。", page)
        self.assertNotIn('data-testid="verdict">只对特定人群值得。', page)

    def test_known_conditional_match_requires_personalized_verdict(self):
        payload = json.loads(QUICK_FIXTURE.read_text(encoding="utf-8"))
        payload["personal_match"] = "matched"
        temp, _, result = self.run_builder(payload, include_bundle=False)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "conditional cards with a known personal_match require personalized_verdict",
            result.stderr,
        )

    def test_matched_conditional_verdict_must_give_an_action_not_only_match_status(self):
        payload = json.loads(QUICK_FIXTURE.read_text(encoding="utf-8"))
        payload["personal_match"] = "matched"
        payload["personalized_verdict"] = "你符合补充条件。"
        temp, _, result = self.run_builder(payload, include_bundle=False)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "matched conditional personalized_verdict must give a direct affirmative action",
            result.stderr,
        )

    def test_known_personal_match_requires_intake_evidence(self):
        payload = json.loads(QUICK_FIXTURE.read_text(encoding="utf-8"))
        payload["personal_match"] = "matched"
        payload["personalized_verdict"] = "可以补充。"
        payload["suitability"]["intake_summary"] = []
        temp, _, result = self.run_builder(payload, include_bundle=False)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("known personal_match requires suitability.intake_summary", result.stderr)

    def test_reports_three_minute_quick_path_sla_and_visible_overrun(self):
        payload = json.loads(QUICK_FIXTURE.read_text(encoding="utf-8"))
        temp, _, result = self.run_builder(payload, include_bundle=False, intake_seconds_ago=120)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["quick_sla_met"])
        self.assertEqual(report["quick_sla_seconds"], 180)

        payload = json.loads(QUICK_FIXTURE.read_text(encoding="utf-8"))
        temp, base, result = self.run_builder(payload, include_bundle=False, intake_seconds_ago=240)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["quick_sla_met"])
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn("超过3分钟目标", page)

    def test_quick_card_requires_three_distinct_source_roles(self):
        payload = json.loads(QUICK_FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["quick_sources"] = payload["research"]["quick_sources"][:2]
        temp, _, result = self.run_builder(payload, include_bundle=False)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("at least three quick_sources", result.stderr)

    def test_coverage_limited_card_allows_and_displays_missing_source_role(self):
        payload = json.loads(QUICK_FIXTURE.read_text(encoding="utf-8"))
        payload["card_state"] = "coverage_limited"
        payload["status_detail"] = "权威长期安全资料尚未核验，按当前覆盖降级交付。"
        payload["verdict"] = "insufficient"
        payload["research"]["quick_sources"] = payload["research"]["quick_sources"][:2]
        temp, base, result = self.run_builder(payload, include_bundle=False)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn("证据覆盖受限，需要全文或人工确认", page)
        self.assertIn("尚缺少的来源角色", page)
        self.assertIn("权威安全资料", page)

    def test_coverage_limited_card_rejects_positive_purchase_verdict(self):
        payload = json.loads(QUICK_FIXTURE.read_text(encoding="utf-8"))
        payload["card_state"] = "coverage_limited"
        payload["research"]["quick_sources"] = payload["research"]["quick_sources"][:2]
        temp, _, result = self.run_builder(payload, include_bundle=False)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("coverage-limited cards require verdict insufficient or avoid", result.stderr)

    def test_builds_hot_cache_card_without_network_or_pubmed_bundle(self):
        payload = json.loads(CACHED_FIXTURE.read_text(encoding="utf-8"))
        pack_temp = tempfile.TemporaryDirectory(prefix="consumer-cache-pack-")
        self.addCleanup(pack_temp.cleanup)
        pack_path = Path(pack_temp.name) / "pack.json"
        research = payload["research"]
        search = research["search"]
        pack_path.write_text(
            json.dumps(
                {
                    "schema_version": "nutrition-evidence-pack-v1",
                    "topic_id": research["cache_topic_id"],
                    "searched_at": research["updated"],
                    "evidence_passport": {
                        "records_found": search["records_found"],
                        "records_exported": search["records_exported"],
                        "records_screened": search["records_screened"],
                        "full_text_unavailable": research["evidence_access"]["full_text_unavailable"],
                        "sources": research["sources"],
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        temp, base, result = self.run_builder(
            payload,
            include_bundle=False,
            evidence_pack=pack_path,
        )
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["evidence_pack_verified"])
        self.assertFalse(report["evidence_bundle_verified"])
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn("L1-Audited 完整审计（缓存命中）", page)
        self.assertIn("本次未重复联网", page)
        self.assertIn("可复现的 PubMed 检索", page)

    def test_updated_recommendation_requires_visible_reason(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["card_state"] = "recommendation_updated"
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires previous_verdict and change_reason", result.stderr)

        payload["previous_verdict"] = "只对特定人群值得。"
        payload["change_reason"] = "完整审计发现直接研究不支持预期的日常获益。"
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn('data-testid="revision-notice"', page)
        self.assertIn("完整审计后建议发生变化", page)

    def test_quick_verification_can_show_a_visible_recommendation_update(self):
        payload = json.loads(QUICK_FIXTURE.read_text(encoding="utf-8"))
        payload["card_state"] = "recommendation_updated"
        payload["previous_verdict"] = "不太值得买。"
        payload["change_reason"] = "用户补充的膳食信息显示本人符合预先定义的补充条件。"
        payload["personal_match"] = "matched"
        payload["personalized_verdict"] = "可以补充，但按标签剂量通常已经足够。"
        temp, base, result = self.run_builder(payload, include_bundle=False)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["card_state"], "recommendation_updated")
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn('data-testid="revision-notice"', page)
        self.assertIn("此前建议", page)
        self.assertIn("用户补充的膳食信息", page)
        self.assertIn("快速核验，未正式评级", page)

    def test_rejects_first_screen_over_150_characters(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["effect_ceiling"] = "很长" * 80
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("maximum is 150", result.stderr)

    def test_escapes_content_and_drops_unsafe_source_url(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["title"] = "<script>alert(1)</script>"
        payload["research"]["sources"][0]["url"] = "javascript:alert(1)"
        payload["research"]["adjudication"][0]["source"] = "<img src=x onerror=alert(1)>"
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertNotIn('href="javascript:', page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn("<img src=x", page)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", page)

    def test_accepts_legacy_pico_field(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["pico"] = payload["research"].pop("picos")
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn("PICOS 与随访", page)

    def test_renders_pre_evidence_intake_and_accepts_legacy_questions(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn("本次已采用的信息", page)
        self.assertIn("用户选择跳过", page)
        self.assertIn("仍可能改变建议的信息", page)

        payload["suitability"]["questions"] = payload["suitability"].pop("remaining_uncertainties")
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("仍可能改变建议的信息", (base / "answer.html").read_text(encoding="utf-8"))

    def test_trial_verdict_requires_and_renders_bounded_protocol(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["verdict"] = "trial"
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires why.self_trial", result.stderr)

        payload["why"]["self_trial"] = {
            "type": "structured_self_trial",
            "target": "晨起主观疲劳",
            "baseline": "先连续记录 7 天",
            "plan": "一次只试一个固定产品 14 天",
            "outcome_measure": "每日 0–10 分疲劳评分",
            "success_rule": "平均改善至少 2 分并维持 1 周",
            "stop_rules": ["出现明显不适或症状恶化就停用"],
            "confounder_controls": ["尽量保持睡眠时长和咖啡因稳定"],
        }
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn("可以低风险试用。", page)
        self.assertIn("怎么试，才不容易骗到自己", page)
        self.assertIn("平均改善至少 2 分", page)

    def test_non_trial_verdict_rejects_self_trial_protocol(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["why"]["self_trial"] = {"type": "structured_self_trial"}
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("only allowed when verdict is trial", result.stderr)

    def test_accepts_legacy_conflicts_field_and_optional_adjudication(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["conflicts"] = payload["research"].pop("funding")
        payload["research"].pop("adjudication")
        payload["research"].pop("what_would_change")
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn("资金与利益冲突", page)
        self.assertNotIn("来源为何看似矛盾", page)

    def test_rejects_payload_without_certainty_method(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"].pop("certainty_method")
        payload["research"].pop("certainty_scope")
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("certainty_method must be a non-empty string", result.stderr)

    def test_renders_source_grade_path(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["certainty_method"] = "source_grade"
        payload["research"]["certainty_scope"] = "引用可信综述的结局级 GRADE，并完成 PubMed 更新检索。"
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn("引用来源已有 GRADE", page)

    def test_rejects_unknown_certainty_method_or_missing_scope(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["certainty_method"] = "instant_grade"
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("certainty_method must be one of", result.stderr)

        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["certainty_scope"] = ""
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("certainty_scope must be a non-empty string", result.stderr)

    def test_rejects_missing_search_audit_or_grade_domains(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"].pop("search")
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("research.search must be an object", result.stderr)

        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["outcomes"][0].pop("grade_domains")
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("grade_domains must be an object", result.stderr)

    def test_rejects_false_complete_counts_and_incomplete_definitive_verdict(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["search"]["records_exported"] = 1
        payload["research"]["search"]["records_screened"] = 1
        payload["research"]["search"]["full_text_assessed"] = 1
        payload["research"]["search"]["reports_included"] = 1
        payload["research"]["search"]["studies_included"] = 1
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("complete_retrieval requires", result.stderr)

        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["search"]["complete_retrieval"] = False
        payload["research"]["search"]["records_exported"] = 1
        payload["research"]["search"]["records_screened"] = 1
        payload["research"]["search"]["full_text_assessed"] = 1
        payload["research"]["search"]["reports_included"] = 1
        payload["research"]["search"]["studies_included"] = 1
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires verdict insufficient or avoid", result.stderr)

    def test_grade_informed_cannot_masquerade_as_formal_grade(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["certainty_method"] = "grade_informed"
        payload["research"]["certainty"] = "低"
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("must say it is not formally rated", result.stderr)

    def test_provisional_grade_shows_verified_full_text_prompt(self):
        payload = json.loads(FISH_FIXTURE.read_text(encoding="utf-8"))
        temp, base, result = self.run_builder(
            payload,
            manifest=FISH_MANIFEST,
            ris=FISH_RIS,
            screening=FISH_SCREENING,
        )
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn('data-testid="full-text-notice"', page)
        self.assertNotIn("<dialog", page)
        self.assertIn("还有 13 篇候选文献未取得全文", page)
        self.assertIn("暂定中等", page)
        self.assertIn("上传", page)

    def test_provisional_grade_rejects_unverified_missing_count(self):
        payload = json.loads(FISH_FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["evidence_access"]["full_text_unavailable"] = 12
        temp, _, result = self.run_builder(
            payload,
            manifest=FISH_MANIFEST,
            ris=FISH_RIS,
            screening=FISH_SCREENING,
        )
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("abstract-only count", result.stderr)

    def test_rejects_evidence_bundle_mismatch(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="evidence-bundle-") as temp_dir:
            bad_manifest = Path(temp_dir) / "manifest.json"
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            manifest["total_hits"] = 999
            bad_manifest.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            temp, _, result = self.run_builder(payload, manifest=bad_manifest)
            self.addCleanup(temp.cleanup)
            self.assertEqual(result.returncode, 2)
            self.assertIn("total_hits does not match", result.stderr)


if __name__ == "__main__":
    unittest.main()
