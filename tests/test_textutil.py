import unittest
import tests.conftest_path  # noqa: F401
from wami import textutil as T


class NormTsTest(unittest.TestCase):
    def test_fractional_offset(self):
        """Python 3.10 fromisoformat が拒否するパターン: fractional + offset."""
        result = T.norm_ts("2026-04-06T14:16:32.334000+00:00")
        self.assertTrue(result, "norm_ts should return non-empty string")
        self.assertTrue(result.startswith("2026-04-06T14:16:32"))

    def test_z_suffix_fractional(self):
        result = T.norm_ts("2026-01-05T10:00:00.000Z")
        self.assertTrue(result, "norm_ts should return non-empty string")
        self.assertTrue(result.startswith("2026-01-05T10:00:00"))

    def test_garbage(self):
        self.assertEqual(T.norm_ts("garbage"), "")


class TextUtilTest(unittest.TestCase):
    def test_is_noise_markers(self):
        self.assertTrue(T.is_noise("<command-name>foo</command-name>"))
        self.assertTrue(T.is_noise("<system-reminder>x"))
        self.assertTrue(T.is_noise("<local-command-stdout>"))
        self.assertTrue(T.is_noise("[Request interrupted by user]"))
        self.assertTrue(T.is_noise("   "))            # 공백뿐
        self.assertFalse(T.is_noise("why is X faster than Y?"))
        self.assertFalse(T.is_noise("이 설계 비판해줘"))
        # 실제 질문이 <tag>로 시작하더라도 노이즈가 아님 (false-positive 방지)
        self.assertFalse(T.is_noise("<div> 이 태그 왜 안 닫히나요?"))
        self.assertFalse(T.is_noise("<MyComponent> 컴포넌트 리뷰해줘"))
        # Task 13 real-data: 실제 로그에서 확인된 시스템 주입 태그
        self.assertTrue(T.is_noise("<task-notification>done</task-notification>"))
        self.assertTrue(T.is_noise("<environment_context>...</environment_context>"))
        self.assertTrue(T.is_noise("<subagent_notification>running</subagent_notification>"))
        self.assertTrue(T.is_noise("<task>some system task</task>"))

    def test_is_noise_injected_agents(self):
        """실데이터에서 확인된 claude-mem·스킬·훅·요약 주입(user 턴의 ~50%)을 거른다."""
        # claude-mem 주입
        self.assertTrue(T.is_noise("Hello memory agent, you are continuing the session"))
        self.assertTrue(T.is_noise("<observed_from_primary_session>\n  <what>"))
        self.assertTrue(T.is_noise("--- MODE SWITCH: PROGRESS SUMMARY --- ⚠️"))
        self.assertTrue(T.is_noise("You are a Claude-Mem, a specialized observation agent"))
        self.assertTrue(T.is_noise("You are Claude-Mem, an agent"))
        self.assertTrue(T.is_noise("You are extracting a structured summary of the session"))
        # Claude Code 시스템/스킬/훅 주입
        self.assertTrue(T.is_noise("Base directory for this skill: /Users/x/skill"))
        self.assertTrue(T.is_noise("This session is being continued from a previous conversation"))
        self.assertTrue(T.is_noise("Continue from where you left off."))
        self.assertTrue(T.is_noise("[Your previous response had no visible output"))
        self.assertTrue(T.is_noise("Stop hook feedback: You MUST call the tool"))
        self.assertTrue(T.is_noise("A session-scoped Stop hook is now active with"))
        # false-positive 방지: 본문에 들어간 진짜 질문은 노이즈 아님(startswith 만 검사)
        self.assertFalse(T.is_noise("how do I build a memory agent in python?"))
        self.assertFalse(T.is_noise("이 claude-mem 플러그인 구조 설명해줘"))
        self.assertFalse(T.is_noise("이 Stop hook 어떻게 만들어?"))

    def test_has_code_block(self):
        self.assertTrue(T.has_code_block("see this:\n```py\nx=1\n```"))
        self.assertFalse(T.has_code_block("no code here"))

    def test_tokens_lowercase_and_stopwords(self):
        toks = T.tokens("Why is the Cache Faster? 왜 캐시가 빠른가")
        self.assertIn("cache", toks)
        self.assertIn("faster", toks)
        self.assertIn("캐시", toks)        # 끝 조사 '가' 제거됨
        self.assertNotIn("캐시가", toks)   # 조사 붙은 형태는 토큰이 아님
        self.assertNotIn("the", toks)   # 영어 불용어 제거
        self.assertNotIn("is", toks)

    def test_strip_josa(self):
        self.assertEqual(T._strip_josa("도커에서"), "도커")
        self.assertEqual(T._strip_josa("쿠버네티스를"), "쿠버네티스")
        self.assertEqual(T._strip_josa("캐시가"), "캐시")
        # stem 이 2자 미만이 되면 떼지 않는다(짧은 토큰 보호)
        self.assertEqual(T._strip_josa("에서"), "에서")

    def test_korean_stopwords_filtered(self):
        # "API에서" → 영문 'api' + 한글 '에서'; '에서'(조사 단독)는 제거
        toks = T.tokens("API에서 docker 설정")
        self.assertIn("api", toks)
        self.assertIn("docker", toks)
        self.assertIn("설정", toks)
        self.assertNotIn("에서", toks)

    def test_english_code_noise_filtered(self):
        toks = T.tokens("return name line each step kubernetes")
        for noise in ("return", "name", "line", "each", "step"):
            self.assertNotIn(noise, toks)
        self.assertIn("kubernetes", toks)   # 진짜 주제어는 남는다

    def test_metaskill_signals(self):
        sig = T.metaskill_signals("이거 비판해주고 정말 맞는지 검증해줘")
        self.assertGreaterEqual(sig["critique"], 1)
        self.assertGreaterEqual(sig["verify"], 1)
        sig2 = T.metaskill_signals("just do it")
        self.assertEqual(sig2["critique"], 0)

    def test_metaskill_delegate(self):
        sig = T.metaskill_signals("네가 알아서 추천해줘")
        self.assertGreaterEqual(sig["delegate"], 1)
        # plain question should not trigger delegate
        plain = T.metaskill_signals("how do I print in python")
        self.assertEqual(plain["delegate"], 0)

    def test_metaskill_counter(self):
        sig = T.metaskill_signals("왜 안 되는지 근거를 줘")
        self.assertGreaterEqual(sig["counter"], 1)
        # plain question should not trigger counter
        plain = T.metaskill_signals("how do I print in python")
        self.assertEqual(plain["counter"], 0)

    def test_is_multistep(self):
        self.assertTrue(T.is_multistep("1. do a\n2. do b\n3. do c"))
        self.assertTrue(T.is_multistep("먼저 A 하고 그다음 B 해줘"))
        self.assertFalse(T.is_multistep("just one thing"))


class ClassifyGenreTest(unittest.TestCase):
    """질문 의도 장르 분류(heuristic v1) — 결정적·양언어."""

    def test_debug(self):
        self.assertEqual(T.classify_genre("이거 왜 안 돼? 에러 고쳐줘"), "debug")
        self.assertEqual(T.classify_genre("fix the TypeError crash"), "debug")
        self.assertEqual(T.classify_genre("this doesn't work anymore"), "debug")

    def test_build(self):
        self.assertEqual(T.classify_genre("how do I add a login button"), "build")
        self.assertEqual(T.classify_genre("로그인 기능 구현해줘"), "build")

    def test_understand(self):
        self.assertEqual(T.classify_genre("what is a closure in JS"), "understand")
        self.assertEqual(T.classify_genre("이 코드 동작 원리 설명해줘"), "understand")
        self.assertEqual(T.classify_genre("how does the event loop work"), "understand")

    def test_improve(self):
        self.assertEqual(T.classify_genre("이 루프 최적화해줘"), "improve")
        self.assertEqual(T.classify_genre("refactor this to be cleaner"), "improve")

    def test_other_fallback(self):
        self.assertEqual(T.classify_genre("ㅁㄴㅇㄹ"), "other")
        self.assertEqual(T.classify_genre(""), "other")
        self.assertEqual(T.classify_genre(None), "other")

    def test_priority_debug_over_build(self):
        # "구현했는데 에러" → 에러(debug)가 구현(build)보다 우선(첫 매치 = 더 구체적)
        self.assertEqual(T.classify_genre("로그인 구현했는데 에러나"), "debug")

    def test_deterministic_and_in_genres(self):
        for txt in ["fix bug", "implement X", "what is Y", "optimize Z", "zzz"]:
            self.assertIn(T.classify_genre(txt), T.GENRES)
        self.assertEqual(T.classify_genre("fix bug"), T.classify_genre("fix bug"))
