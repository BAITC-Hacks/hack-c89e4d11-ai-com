"""Терминальный FAQ-бот для репетиции HackAlem AI."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable


DEFAULT_FAQ_PATH = Path(__file__).with_name("faq.txt")
FALLBACK_ANSWER = "не знаю"
EXIT_COMMANDS = {"выход", "exit", "quit", "q"}


@dataclass(frozen=True)
class FAQEntry:
    question: str
    answer: str
    keywords: frozenset[str]


def normalize(text: str) -> str:
    """Приводит текст к форме, удобной для сравнения."""
    return " ".join(re.findall(r"[a-zа-я0-9]+", text.casefold().replace("ё", "е")))


def tokens(text: str) -> set[str]:
    normalized = normalize(text)
    return set(normalized.split()) if normalized else set()


def load_faq(path: Path = DEFAULT_FAQ_PATH) -> list[FAQEntry]:
    """Загружает и валидирует ровно пять FAQ-записей."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Файл FAQ не найден: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Некорректный JSON в {path}: {exc}") from exc

    if not isinstance(raw, list) or len(raw) != 5:
        raise ValueError("faq.txt должен содержать ровно 5 записей")

    entries: list[FAQEntry] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Запись {index} должна быть объектом")

        question = item.get("question")
        answer = item.get("answer")
        keywords = item.get("keywords")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"У записи {index} отсутствует вопрос")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(f"У записи {index} отсутствует ответ")
        if not isinstance(keywords, list) or not keywords:
            raise ValueError(f"У записи {index} отсутствуют ключевые слова")
        if not all(isinstance(word, str) and normalize(word) for word in keywords):
            raise ValueError(f"У записи {index} некорректные ключевые слова")

        entries.append(
            FAQEntry(
                question=question.strip(),
                answer=answer.strip(),
                keywords=frozenset(normalize(word) for word in keywords),
            )
        )
    return entries


def match_score(user_question: str, entry: FAQEntry) -> tuple[float, int]:
    """Возвращает итоговую оценку и число совпавших ключевых слов."""
    normalized = normalize(user_question)
    query_tokens = tokens(normalized)
    keyword_hits = len(query_tokens & entry.keywords)
    keyword_score = min(keyword_hits / 2, 1.0)
    phrase_score = SequenceMatcher(None, normalized, normalize(entry.question)).ratio()
    return 0.72 * keyword_score + 0.28 * phrase_score, keyword_hits


def find_answer(user_question: str, entries: Iterable[FAQEntry]) -> str:
    """Находит лучший безопасный ответ либо возвращает «не знаю»."""
    if not normalize(user_question):
        return FALLBACK_ANSWER

    ranked = sorted(
        ((match_score(user_question, entry), entry) for entry in entries),
        key=lambda pair: pair[0][0],
        reverse=True,
    )
    if not ranked:
        return FALLBACK_ANSWER

    (best_score, keyword_hits), best_entry = ranked[0]
    phrase_score = SequenceMatcher(
        None, normalize(user_question), normalize(best_entry.question)
    ).ratio()

    # Хотя бы одно смысловое ключевое слово обязательно. Это не даёт боту
    # уверенно отвечать на посторонние вопросы из-за случайного сходства строк.
    if keyword_hits >= 1 and (best_score >= 0.50 or phrase_score >= 0.62):
        return best_entry.answer
    return FALLBACK_ANSWER


def run_chat(entries: list[FAQEntry]) -> None:
    print("FAQ-бот HackAlem AI. Задайте вопрос или напишите «выход».")
    while True:
        try:
            question = input("Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            return

        if normalize(question) in EXIT_COMMANDS:
            print("Бот: До свидания!")
            return
        print(f"Бот: {find_answer(question, entries)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FAQ-бот на 5 вопросов")
    parser.add_argument(
        "--faq",
        type=Path,
        default=DEFAULT_FAQ_PATH,
        help="путь к faq.txt",
    )
    parser.add_argument(
        "--once",
        metavar="ВОПРОС",
        help="ответить на один вопрос и завершить работу",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        entries = load_faq(args.faq)
    except ValueError as exc:
        print(f"Ошибка: {exc}")
        return 1

    if args.once is not None:
        print(find_answer(args.once, entries))
    else:
        run_chat(entries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
