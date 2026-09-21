import unittest
from pathlib import Path

from bot import FALLBACK_ANSWER, find_answer, load_faq, normalize


class FAQBotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entries = load_faq()

    def test_exactly_five_entries_are_loaded(self) -> None:
        self.assertEqual(len(self.entries), 5)

    def test_each_topic_is_recognized(self) -> None:
        cases = {
            "Когда дедлайн?": "22 сентября",
            "Сколько участников в команде?": "до 3 человек",
            "Какой у нас трек?": "LLM-приложения",
            "Что загружать для сдачи?": "репозиторий",
            "Будет денежный приз?": "призового фонда нет",
        }
        for question, expected_fragment in cases.items():
            with self.subTest(question=question):
                self.assertIn(expected_fragment, find_answer(question, self.entries))

    def test_unknown_question_has_safe_fallback(self) -> None:
        self.assertEqual(
            find_answer("Какая завтра погода в Алматы?", self.entries),
            FALLBACK_ANSWER,
        )

    def test_empty_question_has_safe_fallback(self) -> None:
        self.assertEqual(find_answer("   ", self.entries), FALLBACK_ANSWER)

    def test_normalization_is_case_and_punctuation_insensitive(self) -> None:
        self.assertEqual(normalize("  ПРИЗЫ?! Ёлка  "), "призы елка")

    def test_invalid_faq_size_is_rejected(self) -> None:
        path = Path(__file__).with_name(".invalid-faq-for-test.txt")
        try:
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ровно 5"):
                load_faq(path)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
