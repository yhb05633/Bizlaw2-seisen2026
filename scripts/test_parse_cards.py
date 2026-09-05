import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from parse_cards import (
    split_into_question_blocks,
    parse_block,
    extract_titles,
    split_prompt_and_choices,
    compute_answer_index,
    normalize_choice_text,
    normalize_answer_text,
)


class TestSplitIntoQuestionBlocks(unittest.TestCase):
    def test_splits_heading_style_blocks(self):
        text = (
            "## 第1章 テスト\n\n"
            "#### 第1問（第45回 第3問 3-3）\n"
            "本文A\n\n"
            "##### 【解答・解説】\n"
            "**正解：①**\n\n"
            "#### 第2問（第40回 第1問 1-1）\n"
            "本文B\n\n"
            "##### 【解答・解説】\n"
            "**正解：②**\n"
        )
        blocks = split_into_question_blocks(text)
        self.assertEqual(len(blocks), 2)
        self.assertTrue(blocks[0].startswith("#### 第1問"))
        self.assertTrue(blocks[1].startswith("#### 第2問"))

    def test_splits_plain_text_blocks_without_heading_markers(self):
        text = (
            "損害賠償責任\n\n"
            "第1問\n"
            "本文A\n\n"
            "解答：⑤\n\n"
            "【解説】\n"
            "説明A\n\n"
            "第2問\n"
            "本文B\n\n"
            "解答：①\n\n"
            "【解説】\n"
            "説明B\n"
        )
        blocks = split_into_question_blocks(text)
        self.assertEqual(len(blocks), 2)
        self.assertTrue(blocks[0].startswith("第1問"))
        self.assertTrue(blocks[1].startswith("第2問"))


class TestParseBlock(unittest.TestCase):
    def test_heading_kaitou_kaisetsu_style(self):
        block = (
            "#### 第1問（第45回 第3問 3-3）\n"
            "**設問**\n"
            "本文の質問です。\n\n"
            "##### 【解答・解説】\n"
            "**正解：③（ア・エ・オ）**\n\n"
            "* **ア：適切である。**説明その1\n"
        )
        result = parse_block(block)
        self.assertEqual(result["examRef"], "第45回 第3問 3-3")
        self.assertEqual(result["answer"], "③（ア・エ・オ）")
        self.assertIn("本文の質問です。", result["question"])
        self.assertNotIn("設問", result["question"])
        self.assertIn("説明その1", result["explanation"])

    def test_separate_kaitou_and_kaisetsu_headings(self):
        block = (
            "## 第1問（第45回 第10問 10-1）\n"
            "本文です。\n\n"
            "### 解答\n"
            "③\n\n"
            "### 解説\n"
            "説明文です。\n"
        )
        result = parse_block(block)
        self.assertEqual(result["answer"], "③")
        self.assertIn("説明文です。", result["explanation"])
        self.assertNotIn("解説", result["explanation"].split("\n")[0])

    def test_bold_kaitou_then_kaisetsu(self):
        block = (
            "#### 第1問（第48回 第2問 2-2）\n"
            "**設問**\n"
            "本文です。\n\n"
            "**解答**\n"
            "1\n\n"
            "**解説**\n"
            "1．説明です。\n"
        )
        result = parse_block(block)
        self.assertEqual(result["answer"], "1")
        self.assertIn("説明です。", result["explanation"])

    def test_bold_kaitou_kaisetsu_with_inline_seikai(self):
        block = (
            "### 第1問（第44回 第4問 41）\n"
            "**設問**\n"
            "本文です。\n\n"
            "**解答・解説**\n\n"
            "**正解：③**\n\n"
            "* a. 適切である：説明です。\n"
        )
        result = parse_block(block)
        self.assertEqual(result["answer"], "③")
        self.assertIn("説明です。", result["explanation"])

    def test_plain_text_no_markup(self):
        block = (
            "第1問\n"
            "本文です。\n\n"
            "解答：⑤\n\n"
            "【解説】\n"
            "説明です。\n"
        )
        result = parse_block(block)
        self.assertEqual(result["examRef"], "")
        self.assertEqual(result["answer"], "⑤")
        self.assertIn("説明です。", result["explanation"])

    def test_separate_kaitou_heading_with_bold_wrapped_answer(self):
        # Real-data variant (e.g. 10.txt): the "### 解答" heading's value is on
        # its own line, wrapped in markdown bold, with no "正解："/"解答：" prefix.
        block = (
            "## 第1問（第45回 第10問 10-1）\n"
            "本文です。\n\n"
            "---\n\n"
            "### 解答\n"
            "**③**\n\n"
            "---\n\n"
            "### 解説\n\n"
            "* **① 適切でない**：説明です。\n"
        )
        result = parse_block(block)
        self.assertEqual(result["answer"], "③")
        self.assertIn("説明です。", result["explanation"])

    def test_no_boundary_raises(self):
        block = "#### 第1問（第1回 第1問 1-1）\n本文だけで解答がありません。\n"
        with self.assertRaises(ValueError):
            parse_block(block)

    def test_strips_trailing_heading_leaked_from_next_question(self):
        block = (
            "#### 第1問（第1回 第1問 1-1）\n"
            "本文です。\n\n"
            "##### 【解答・解説】\n"
            "**正解：①**\n\n"
            "説明文です。\n\n"
            "### 2 意思表示\n"
        )
        result = parse_block(block)
        self.assertNotIn("意思表示", result["explanation"])
        self.assertIn("説明文です。", result["explanation"])

    def test_strips_trailing_heading_with_ideographic_space(self):
        block = (
            "#### 第1問（第1回 第1問 1-1）\n"
            "本文です。\n\n"
            "##### 【解答・解説】\n"
            "**正解：①**\n\n"
            "説明文です。\n\n"
            "####　株主総会\n"
        )
        result = parse_block(block)
        self.assertNotIn("株主総会", result["explanation"])


class TestExtractTitles(unittest.TestCase):
    def test_extracts_one_title_per_question_various_heading_styles(self):
        text = (
            "## 第１章 テスト\n\n"
            "### 行為能力\n"
            "#### 第1問（第45回 第3問 3-3）\n"
            "本文A\n\n"
            "##### 【解答・解説】\n"
            "**正解：①**\n\n"
            "---\n\n"
            "####　株主総会\n"
            "##### 第2問（第40回 第1問 1-1）\n"
            "本文B\n\n"
            "##### 【解答・解説】\n"
            "**正解：②**\n"
        )
        titles = extract_titles(text)
        self.assertEqual(titles, ["行為能力", "株主総会"])

    def test_falls_back_to_previous_title_when_missing(self):
        text = (
            "### 独占禁止法\n"
            "#### 第1問（第1回 第1問 1-1）\n"
            "本文A\n\n"
            "##### 【解答・解説】\n"
            "**正解：①**\n\n"
            "#### 第2問（第1回 第2問 2-1）\n"
            "本文B\n\n"
            "##### 【解答・解説】\n"
            "**正解：②**\n"
        )
        titles = extract_titles(text)
        self.assertEqual(titles, ["独占禁止法", "独占禁止法"])

    def test_ignores_explanation_bullets_when_falling_back_to_previous_title(self):
        # Real-data variant (chapters 13-16): a subsection title is shared
        # by several consecutive questions, and the first question's
        # explanation contains markdown-bullet per-choice commentary
        # (e.g. "* **ア：適切でない。**"). That bullet line must not be
        # mistaken for the second question's title.
        text = (
            "### 取締役・取締役会\n"
            "#### 第1問（第1回 第1問 1-1）\n"
            "本文A\n\n"
            "##### 【解答・解説】\n"
            "**正解：①**\n\n"
            "* **ア：適切でない。**\n"
            "  説明文がここに入ります。\n\n"
            "#### 第2問（第1回 第2問 2-1）\n"
            "本文B\n\n"
            "##### 【解答・解説】\n"
            "**正解：②**\n"
        )
        titles = extract_titles(text)
        self.assertEqual(titles, ["取締役・取締役会", "取締役・取締役会"])


class TestSplitPromptAndChoices(unittest.TestCase):
    def test_splits_clean_five_choice_question(self):
        question = (
            "次のア〜オのうち適切なものの組み合わせを選びなさい。\n\n"
            "ア．文A\n"
            "イ．文B\n\n"
            "① アイ\n"
            "② **アウ**\n"
            "③ アエ\n"
            "④ アオ\n"
            "⑤ イウ"
        )
        prompt, choices, is_prose = split_prompt_and_choices(question)
        self.assertFalse(is_prose)
        self.assertEqual(len(choices), 5)
        self.assertEqual(choices[0], "① ア・イ")
        self.assertEqual(choices[1], "② ア・ウ")
        self.assertNotIn("*", choices[1])

    def test_supports_six_choices(self):
        lines = "\n".join(f"{c} 選択肢{c}" for c in "①②③④⑤⑥")
        question = "設問文\n\n" + lines
        prompt, choices, is_prose = split_prompt_and_choices(question)
        self.assertFalse(is_prose)
        self.assertEqual(len(choices), 6)

    def test_supports_arabic_markers(self):
        lines = "\n".join(f"{n}．選択肢{n}" for n in range(1, 6))
        question = "設問文\n\n" + lines
        prompt, choices, is_prose = split_prompt_and_choices(question)
        self.assertFalse(is_prose)
        self.assertEqual(len(choices), 5)
        self.assertTrue(choices[0].startswith("①"))

    def test_falls_back_to_prose_when_u_tag_present(self):
        question = "本文①<u>下線部分</u>と②<u>別の下線部分</u>です。"
        prompt, choices, is_prose = split_prompt_and_choices(question)
        self.assertTrue(is_prose)
        self.assertEqual(choices, [])
        self.assertEqual(prompt, question)

    def test_falls_back_to_prose_when_trailing_note_after_choices(self):
        question = (
            "設問文\n\n"
            "① アイ\n"
            "② アウ\n"
            "③ アエ\n\n"
            "※注記があります。"
        )
        prompt, choices, is_prose = split_prompt_and_choices(question)
        self.assertTrue(is_prose)
        self.assertEqual(choices, [])

    def test_falls_back_to_prose_when_choice_has_continuation_line(self):
        question = (
            "設問文\n\n"
            "① 甲「質問1」\n"
            "   乙「回答1」\n"
            "② 甲「質問2」\n"
            "   乙「回答2」\n"
            "③ 甲「質問3」\n"
            "   乙「回答3」"
        )
        prompt, choices, is_prose = split_prompt_and_choices(question)
        self.assertTrue(is_prose)
        self.assertEqual(choices, [])

    def test_extracts_combination_choices_even_with_inline_underline_paragraph(self):
        question = (
            "次の文章中の下線部（a）〜（e）のうち適切なものの組み合わせを選びなさい。\n\n"
            "本文です。（a）<u>下線部分A</u>という記述と、（b）<u>下線部分B</u>という記述があります。\n\n"
            "①（a）（b）（c）\n"
            "②（a）（b）（e）\n"
            "③（a）（d）（e）\n"
            "④（b）（c）（d）\n"
            "⑤（c）（d）（e）"
        )
        prompt, choices, is_prose = split_prompt_and_choices(question)
        self.assertFalse(is_prose)
        self.assertEqual(len(choices), 5)
        self.assertIn("<u>下線部分A</u>", prompt)


class TestComputeAnswerIndex(unittest.TestCase):
    def test_circled_marker(self):
        self.assertEqual(compute_answer_index("④（ア－✕、イ－〇）"), 3)

    def test_bare_circled_marker(self):
        self.assertEqual(compute_answer_index("①"), 0)

    def test_arabic_marker(self):
        self.assertEqual(compute_answer_index("1"), 0)

    def test_unrecognized_returns_none(self):
        self.assertIsNone(compute_answer_index("該当なし"))

    def test_fullwidth_paren_arabic_digit(self):
        # Real-data variant (e.g. 02.txt): the answer is given as a
        # fullwidth-paren arabic digit even though the question's own
        # choices are circled markers. The digit is still a 1-based
        # position into those choices.
        self.assertEqual(compute_answer_index("（2）"), 1)
        self.assertEqual(compute_answer_index("（5）"), 4)


class TestNormalizeChoiceText(unittest.TestCase):
    def test_inserts_nakaguro_between_bare_katakana_letters(self):
        self.assertEqual(normalize_choice_text("アイウ"), "ア・イ・ウ")
        self.assertEqual(normalize_choice_text("アイ"), "ア・イ")
        self.assertEqual(normalize_choice_text("ウエオ"), "ウ・エ・オ")

    def test_leaves_already_separated_katakana_unchanged(self):
        self.assertEqual(normalize_choice_text("ア・イ・ウ"), "ア・イ・ウ")

    def test_leaves_prose_choice_text_unchanged(self):
        text = "商法上、商人である対話者の間においては、契約は効力を失う。"
        self.assertEqual(normalize_choice_text(text), text)

    def test_normalizes_ox_combination_with_comma_and_fullwidth_dash(self):
        self.assertEqual(
            normalize_choice_text("ア－✕、イ－〇、ウ－〇、エ－〇"),
            "ア－✕、イ－〇、ウ－〇、エ－〇",
        )

    def test_normalizes_ox_combination_with_halfwidth_hyphen(self):
        self.assertEqual(
            normalize_choice_text("ア-〇、イ-✕、ウ-✕、エ-✕"),
            "ア－〇、イ－✕、ウ－✕、エ－✕",
        )

    def test_normalizes_ox_combination_with_colon_and_slash(self):
        self.assertEqual(
            normalize_choice_text("ア：〇 / イ：✕ / ウ：〇 / エ：〇 / オ：✕"),
            "ア－〇、イ－✕、ウ－〇、エ－〇、オ－✕",
        )

    def test_normalizes_ox_combination_with_em_dash_and_irregular_spacing(self):
        self.assertEqual(
            normalize_choice_text("ア―✕ イ―✕  ウ―〇  エ―✕  オ―✕"),
            "ア－✕、イ－✕、ウ－〇、エ－✕、オ－✕",
        )


class TestNormalizeAnswerText(unittest.TestCase):
    def test_normalizes_ox_combination_inside_parens(self):
        self.assertEqual(
            normalize_answer_text("①（ア：〇 イ：〇 ウ：✕ エ：〇 オ：〇）"),
            "①（ア－〇、イ－〇、ウ－✕、エ－〇、オ－〇）",
        )

    def test_normalizes_bare_katakana_combo_inside_parens(self):
        self.assertEqual(normalize_answer_text("③（アエオ）"), "③（ア・エ・オ）")

    def test_leaves_already_canonical_answer_unchanged(self):
        self.assertEqual(
            normalize_answer_text("④（ア－✕、イ－〇、ウ－〇、エ－✕）"),
            "④（ア－✕、イ－〇、ウ－〇、エ－✕）",
        )

    def test_leaves_answer_without_parens_unchanged(self):
        self.assertEqual(normalize_answer_text("③"), "③")


if __name__ == "__main__":
    unittest.main()
