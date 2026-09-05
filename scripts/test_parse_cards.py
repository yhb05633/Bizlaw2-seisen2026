import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from parse_cards import split_into_question_blocks, parse_block


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

    def test_no_boundary_raises(self):
        block = "#### 第1問（第1回 第1問 1-1）\n本文だけで解答がありません。\n"
        with self.assertRaises(ValueError):
            parse_block(block)


if __name__ == "__main__":
    unittest.main()
